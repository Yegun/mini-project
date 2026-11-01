"""식품을 만들고 고치는 규칙을 한 곳에 모았다 (검사 → 기한 계산 → 저장).

창구(routers)는 요청을 받아 여기로 넘기기만 하고, 저장 확정(commit)은 창구가 한다.
"""

import sqlite3
from datetime import date

from app import foods_store
from app.db import rules_repo
from app.calc import (
    expiry_from_days,
    new_expiry_after_storage_change,
    remaining_days_after_storage_change,
    shift_expiry,
)
from app.errors import ApiError
from app.validation import (
    ValidationError,
    check_expiry_not_in_past,
    check_purchase_not_after_expiry,
    parse_date,
    resolve_manual_expiry,
    validate_quantity,
    validate_storage,
    validate_storage_allowed,
    validate_text,
)


STORAGE_ORDER = ("room", "fridge", "freezer")


def allowed_storages(rule: dict) -> set[str]:
    return {info["storage"] for info in rule["storages"] if info["allowed"]}


def not_allowed_storages(rule: dict) -> list[str]:
    """고를 수 없는("불가") 보관 방법. 상온·냉장·냉동 순서 (D-005)."""
    allowed = allowed_storages(rule)
    return [storage for storage in STORAGE_ORDER if storage not in allowed]


def max_days(rule: dict, storage: str) -> int | None:
    """그 보관 방법의 최대 보관 기간(일). 불가한 방법이면 None."""
    for info in rule["storages"]:
        if info["storage"] == storage:
            return info["max_days"]
    return None


def rule_max_days(rule: dict, storage: str) -> int:
    """허용된 보관 방법인데 기간이 비어 있으면 규칙표 DB 가 잘못된 것이다."""
    days = max_days(rule, storage)
    if days is None:
        raise ApiError(500, "load_failed")
    return days


def register_rule_food(
    conn: sqlite3.Connection, rules_conn: sqlite3.Connection, raw: dict, today: date
) -> dict:
    """A3 규칙표 식품 등록. 기한 = 구매일 + 보관 방법별 일수 (V-08)."""
    name = validate_text(raw["name"], "name")
    quantity = validate_quantity(raw["quantity"])
    unit = validate_text(raw["unit"], "unit")
    purchase_date = parse_date(raw["purchase_date"], "purchase_date")
    storage = validate_storage(raw["storage"])

    rule = rules_repo.get_rule_by_name(rules_conn, name)
    if rule is None:
        raise ValidationError("name", "not_in_rules")
    validate_storage_allowed(storage, allowed_storages(rule))

    expiry_date = expiry_from_days(purchase_date, rule_max_days(rule, storage))
    check_purchase_not_after_expiry(purchase_date, expiry_date)
    return foods_store.create_food(
        conn,
        name=name,
        storage=storage,
        quantity=quantity,
        unit=unit,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        source="rule",
    )


def register_manual_food(conn: sqlite3.Connection, raw: dict, today: date) -> dict:
    """A4 직접 등록. 직접 적은 기한이 그대로 쓰인다 (US-003)."""
    name = validate_text(raw["name"], "name")
    quantity = validate_quantity(raw["quantity"])
    unit = validate_text(raw["unit"], "unit")
    purchase_date = parse_date(raw["purchase_date"], "purchase_date")
    storage = validate_storage(raw["storage"])
    expiry_date = resolve_manual_expiry(
        purchase_date, raw["expiry_date"], raw["expiry_in_days"], today
    )
    return foods_store.create_food(
        conn,
        name=name,
        storage=storage,
        quantity=quantity,
        unit=unit,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        source="manual",
    )


def _is_given(value) -> bool:
    return value is not None and value != ""


def change_storage(
    conn: sqlite3.Connection, rules_conn: sqlite3.Connection, food: dict, raw: dict, today: date
) -> dict:
    """A7 보관 방법 변경.

    규칙표 식품은 지금까지 쓴 비율을 새 방법에 환산해 기한을 다시 구한다 (D-006).
    직접 등록 식품은 계산할 규칙표가 없어서 새 기한을 직접 적어야 한다 (D-023).
    """
    storage = validate_storage(raw["storage"])
    if storage == food["storage"]:
        return food  # 같은 방법이면 기한 그대로 성공 처리 (DATA-MODEL 2절)

    if food["source"] == "manual":
        if not _is_given(raw["expiry_date"]):
            raise ApiError(409, "expiry_required", "expiry_date")
        expiry_date = parse_date(raw["expiry_date"], "expiry_date")
        check_expiry_not_in_past(expiry_date, today)
        check_purchase_not_after_expiry(food["purchase_date"], expiry_date)
    else:
        if _is_given(raw["expiry_date"]):
            raise ValidationError("expiry_date", "invalid")
        rule = rules_repo.get_rule_by_name(rules_conn, food["name"])
        if rule is None:
            raise ApiError(500, "load_failed")
        validate_storage_allowed(storage, allowed_storages(rule))
        current_max = rule_max_days(rule, food["storage"])
        new_max = rule_max_days(rule, storage)
        remaining = remaining_days_after_storage_change(
            food["purchase_date"], today, current_max, new_max
        )
        expiry_date = new_expiry_after_storage_change(
            food["purchase_date"], today, current_max, new_max
        )
        # 계산 결과가 음수면 바꿀 수 없다. 이미 지난 식품은 새 기한이 오늘보다 뒤일 때만 바꿀 수 있다 (D-006).
        already_expired = food["expiry_date"] < today
        if remaining < 0 or (already_expired and expiry_date <= today):
            raise ValidationError("storage", "change_blocked")

    return foods_store.update_food(conn, food["id"], storage=storage, expiry_date=expiry_date)


def _expiry_keeping_ratio(
    purchase_date: date, today: date, current_max_days: int, new_max_days: int
) -> date:
    """이름을 바꿀 때 지금까지 쓴 비율을 새 규칙표 기간에 이어받는다 (D-004, OQ-11)."""
    if current_max_days <= 0:
        # 구매한 날이 기한이던 식품이라 이어받을 비율이 없다. 남은 기간 0일로 본다.
        return max(today, purchase_date)
    return new_expiry_after_storage_change(purchase_date, today, current_max_days, new_max_days)


def change_info(
    conn: sqlite3.Connection,
    rules_conn: sqlite3.Connection,
    food: dict,
    fields: dict,
    today: date,
) -> dict:
    """A6 정보 수정 (이름, 구매일, 수량, 단위). fields 에는 보낸 칸만 들어 있다.

    이름과 구매일을 한 번에 고치면 이름 변경을 먼저 처리하고, 그 기한에 구매일 이동을 적용한다 (D-026).
    """
    updates = {}
    new_name = validate_text(fields["name"], "name") if "name" in fields else food["name"]
    if "quantity" in fields:
        updates["quantity"] = validate_quantity(fields["quantity"])
    if "unit" in fields:
        updates["unit"] = validate_text(fields["unit"], "unit")
    new_purchase = (
        parse_date(fields["purchase_date"], "purchase_date")
        if "purchase_date" in fields
        else food["purchase_date"]
    )
    has_expiry_input = _is_given(fields.get("expiry_date"))

    expiry_date = food["expiry_date"]
    source = food["source"]
    name_changed = new_name != food["name"]

    if name_changed:
        rule = rules_repo.get_rule_by_name(rules_conn, new_name)
        if rule is not None:
            # 규칙표에 있는 이름: 규칙표 기준으로 다시 계산한다. 기한은 계산되므로 따로 받지 않는다.
            if has_expiry_input:
                raise ValidationError("expiry_date", "invalid")
            validate_storage_allowed(food["storage"], allowed_storages(rule))
            new_max = rule_max_days(rule, food["storage"])
            if food["source"] == "rule":
                old_rule = rules_repo.get_rule_by_name(rules_conn, food["name"])
                if old_rule is None:
                    raise ApiError(500, "load_failed")
                current_max = rule_max_days(old_rule, food["storage"])
            else:
                # 직접 등록 식품은 처음 잡은 기간(구매일~기한)을 지금 방법의 최대 기간으로 본다.
                current_max = (food["expiry_date"] - food["purchase_date"]).days
            expiry_date = _expiry_keeping_ratio(food["purchase_date"], today, current_max, new_max)
            source = "rule"
        else:
            # 규칙표에 없는 이름: 이미 지난 식품은 못 바꾸고, 새 기한을 직접 적어야 한다.
            if food["expiry_date"] < today:
                raise ValidationError("name", "name_change_blocked")
            if not has_expiry_input:
                raise ApiError(409, "expiry_required", "expiry_date")
            expiry_date = parse_date(fields["expiry_date"], "expiry_date")
            check_expiry_not_in_past(expiry_date, today)
            source = "manual"
    elif has_expiry_input:
        raise ValidationError("expiry_date", "invalid")

    if new_purchase != food["purchase_date"] and source == "rule":
        # 규칙표 식품은 구매일이 움직인 일수만큼 기한도 옮긴다. 직접 적은 기한은 그대로 둔다 (D-024).
        expiry_date = shift_expiry(expiry_date, food["purchase_date"], new_purchase)
    check_purchase_not_after_expiry(new_purchase, expiry_date)

    if name_changed:
        updates["name"] = new_name
    if new_purchase != food["purchase_date"]:
        updates["purchase_date"] = new_purchase
    if expiry_date != food["expiry_date"]:
        updates["expiry_date"] = expiry_date
    if source != food["source"]:
        updates["source"] = source
    return foods_store.update_food(conn, food["id"], **updates)
