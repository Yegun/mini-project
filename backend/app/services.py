"""식품을 만들고 고치는 규칙을 한 곳에 모았다 (검사 → 기한 계산 → 저장).

창구(routers)는 요청을 받아 여기로 넘기기만 하고, 저장 확정(commit)은 창구가 transaction 으로 한다.
저장소(app/db)는 저장만 한다. 검사·기한 계산·규칙표 판단은 여기서 한다 (ARCHITECTURE 5절).
"""
from datetime import date

import psycopg

from app.calc import (
    expiry_from_days,
    new_expiry_after_storage_change,
    remaining_days_after_storage_change,
    shift_expiry,
)
from app.db import foods_repo, rules_repo
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


def disallowed_storages(rule: dict) -> list[str]:
    """고를 수 없는("불가") 보관 방법. 상온·냉장·냉동 순서 (D-005)."""
    allowed = allowed_storages(rule)
    return [storage for storage in STORAGE_ORDER if storage not in allowed]


def rule_max_days(rule: dict, storage: str) -> int:
    """그 보관 방법의 최대 보관 기간(일). 비어 있으면 규칙표 데이터가 잘못된 것이라 server_error 다."""
    for info in rule["storages"]:
        if info["storage"] == storage and info["max_days"] is not None:
            return info["max_days"]
    raise ApiError("server_error")


def _is_given(value) -> bool:
    return value is not None and value != ""


def _day(text: str) -> date:
    return date.fromisoformat(text)


def _basic_fields(raw: dict) -> dict:
    """A2·A3 가 같이 받는 다섯 칸을 API-SPEC 실패 표의 순서대로 검사한다."""
    return {
        "name": validate_text(raw["name"], "name"),
        "unit": validate_text(raw["unit"], "unit"),
        "quantity": validate_quantity(raw["quantity"]),
        "purchase_date": parse_date(raw["purchase_date"], "purchase_date"),
        "storage": validate_storage(raw["storage"]),
    }


def register_rule_food(conn: psycopg.Connection, user_id: str, raw: dict) -> dict:
    """A2 규칙표 식품 등록. 기한 = 구매일 + 보관 방법별 일수 (V-08). 내 식품으로 저장한다.

    이름이 규칙표의 정식 이름이나 별칭이면 등록하고, 별칭으로 보내도 저장되는 이름은 정식 이름이다 (API-SPEC 5절 20번).
    """
    fields = _basic_fields(raw)
    rule = rules_repo.find_rule(conn, fields["name"])
    if rule is None:
        raise ValidationError("name", "rule_not_found")
    validate_storage_allowed(fields["storage"], allowed_storages(rule))

    purchase_date = fields["purchase_date"]
    expiry_date = expiry_from_days(purchase_date, rule_max_days(rule, fields["storage"]))
    check_purchase_not_after_expiry(purchase_date, expiry_date)  # 기한 = 구매일 + 양수 일수라 실제로는 걸리지 않는다
    return foods_repo.create_food(
        conn,
        user_id,
        name=rule["name"],
        storage=fields["storage"],
        quantity=fields["quantity"],
        unit=fields["unit"],
        purchase_date=purchase_date.isoformat(),
        expiry_date=expiry_date.isoformat(),
        source="rule",
    )


def register_manual_food(conn: psycopg.Connection, user_id: str, raw: dict, today: date) -> dict:
    """A3 직접 등록. 직접 적은 기한이 그대로 쓰인다 (US-003). 규칙표에는 더하지 않는다 (D-092).

    규칙표의 이름이나 별칭으로는 직접 등록할 수 없다 (rule_name_exists).
    """
    fields = _basic_fields(raw)
    expiry_date = resolve_manual_expiry(
        fields["purchase_date"], raw["expiry_date"], raw["expiry_in_days"], today
    )
    if rules_repo.find_rule(conn, fields["name"]) is not None:
        raise ValidationError("name", "rule_name_exists")
    return foods_repo.create_food(
        conn,
        user_id,
        name=fields["name"],
        storage=fields["storage"],
        quantity=fields["quantity"],
        unit=fields["unit"],
        purchase_date=fields["purchase_date"].isoformat(),
        expiry_date=expiry_date.isoformat(),
        source="manual",
    )


def _save(conn: psycopg.Connection, user_id: str, food: dict, **updates) -> dict:
    changed = foods_repo.update_food(conn, user_id, food["id"], **updates)
    if changed is None:  # 확인한 뒤 다른 기기에서 처리·삭제했다
        raise ApiError("not_found")
    return changed


def change_storage(
    conn: psycopg.Connection, user_id: str, food: dict, raw: dict, today: date
) -> dict:
    """A6 보관 방법 변경.

    규칙표 식품은 지금까지 쓴 비율을 새 방법에 환산해 기한을 다시 구한다 (D-006).
    직접 등록 식품은 계산할 규칙표가 없어서 새 기한을 직접 적어야 한다 (D-023).
    같은 방법이면 기한 그대로 성공이다 (이 줄이 아래 줄들보다 먼저 적용된다).
    """
    storage = validate_storage(raw["storage"])
    # 기한을 쓰든 안 쓰든 보낸 값의 모양은 검사한다 (2026-11-02 사용자 결정). 올바른데 필요 없으면 무시한다.
    new_expiry_input = (
        parse_date(raw["expiry_date"], "expiry_date") if _is_given(raw["expiry_date"]) else None
    )
    if storage == food["storage"]:
        return food

    purchase_date = _day(food["purchase_date"])
    if food["source"] == "manual":
        if new_expiry_input is None:
            raise ApiError("expiry_required", "expiry_date")
        check_expiry_not_in_past(new_expiry_input, today)
        check_purchase_not_after_expiry(purchase_date, new_expiry_input)
        expiry_date = new_expiry_input
    else:
        rule = rules_repo.get_rule_by_name(conn, food["name"])
        if rule is None:
            # 규칙표 내용이 바뀌었다. 기한을 직접 적게 하는 길은 열지 않는다 (API-SPEC 5절 7번)
            raise ValidationError("storage", "rule_not_found")
        validate_storage_allowed(storage, allowed_storages(rule))
        current_max = rule_max_days(rule, food["storage"])
        new_max = rule_max_days(rule, storage)
        remaining = remaining_days_after_storage_change(purchase_date, today, current_max, new_max)
        expiry_date = new_expiry_after_storage_change(purchase_date, today, current_max, new_max)
        # 계산 결과가 음수면 바꿀 수 없다. 이미 지난 식품은 새 기한이 오늘보다 뒤일 때만 바꿀 수 있다 (D-006, V-10).
        already_expired = _day(food["expiry_date"]) < today
        if remaining < 0 or (already_expired and expiry_date <= today):
            raise ValidationError("storage", "storage_change_not_allowed")

    return _save(conn, user_id, food, storage=storage, expiry_date=expiry_date.isoformat())


def _expiry_keeping_ratio(
    purchase_date: date, today: date, current_max_days: int, new_max_days: int
) -> date:
    """이름을 바꿀 때 지금까지 쓴 비율을 새 규칙표 기간에 이어받는다 (D-004, OQ-11).

    처음 잡은 기간이 0일이면 비율을 구할 수 없어서 새 규칙의 기간 전체를 준다 (2026-11-02 사용자 결정).
    """
    if current_max_days <= 0:
        return expiry_from_days(max(today, purchase_date), new_max_days)
    return new_expiry_after_storage_change(purchase_date, today, current_max_days, new_max_days)


def change_info(
    conn: psycopg.Connection, user_id: str, food: dict, fields: dict, today: date
) -> dict:
    """A5 정보 수정 (이름, 구매일, 수량, 단위). fields 에는 보낸 칸만 들어 있다.

    이름과 구매일을 한 번에 고치면 이름 변경을 먼저 처리하고, 그 기한에 구매일 이동을 적용한다 (D-026).
    """
    purchase_old = _day(food["purchase_date"])
    expiry_old = _day(food["expiry_date"])

    # 입력 검사: 보낸 칸만, API-SPEC 실패 표의 순서대로
    new_name = validate_text(fields["name"], "name") if "name" in fields else food["name"]
    updates: dict = {}
    if "unit" in fields:
        updates["unit"] = validate_text(fields["unit"], "unit")
    if "quantity" in fields:
        updates["quantity"] = validate_quantity(fields["quantity"])
    purchase_new = (
        parse_date(fields["purchase_date"], "purchase_date") if "purchase_date" in fields else purchase_old
    )
    # 기한을 쓰든 안 쓰든 보낸 값의 모양은 검사한다 (2026-11-02 사용자 결정). 올바른데 필요 없으면 무시한다.
    expiry_input = (
        parse_date(fields["expiry_date"], "expiry_date") if _is_given(fields.get("expiry_date")) else None
    )

    expiry = expiry_old
    source = food["source"]
    stored_name = food["name"]
    expiry_decided = False  # 이번 요청이 기한을 새로 정했는가 (구매일 > 기한일 때 어느 칸 탓인지 가른다)

    new_rule = rules_repo.find_rule(conn, new_name) if "name" in fields else None
    stored_new_name = new_rule["name"] if new_rule else new_name  # 별칭으로 보내도 저장되는 이름은 정식 이름
    if "name" in fields and stored_new_name != food["name"]:
        stored_name = stored_new_name
        expiry_decided = True
        if new_rule is not None:
            # 규칙표에 있는 이름: 규칙표 기준으로 다시 계산한다. 기한은 계산되므로 따로 받지 않는다 (보낸 값은 무시).
            validate_storage_allowed(food["storage"], allowed_storages(new_rule))  # DATA-MODEL Q-24 ①
            new_max = rule_max_days(new_rule, food["storage"])
            if food["source"] == "rule":
                # 규칙표는 늘어나기만 해서 옛 이름이 사라지는 일은 없다고 본다 (사용자 설명)
                old_rule = rules_repo.get_rule_by_name(conn, food["name"])
                current_max = rule_max_days(old_rule, food["storage"])
            else:
                # 직접 등록 식품은 처음 잡은 기간(구매일~기한)을 지금 방법의 최대 기간으로 본다 (DATA-MODEL Q-24 ②)
                current_max = (expiry_old - purchase_old).days
            expiry = _expiry_keeping_ratio(purchase_old, today, current_max, new_max)
            source = "rule"
        else:
            # 규칙표에 없는 이름: 이미 지난 식품은 못 바꾸고, 새 기한을 직접 적어야 한다 (V-11, PRD 4-4).
            if expiry_old < today:
                raise ValidationError("name", "rename_expired_not_allowed")
            if expiry_input is None:
                raise ApiError("expiry_required", "expiry_date")
            check_expiry_not_in_past(expiry_input, today)
            expiry = expiry_input
            source = "manual"

    if purchase_new != purchase_old and source == "rule":
        # 규칙표 식품은 구매일이 움직인 일수만큼 기한도 옮긴다. 직접 적은 기한은 그대로 둔다 (D-024).
        expiry = shift_expiry(expiry, purchase_old, purchase_new)
    check_purchase_not_after_expiry(
        purchase_new, expiry, "expiry_date" if expiry_decided else "purchase_date"
    )

    if stored_name != food["name"]:
        updates["name"] = stored_name
    if purchase_new != purchase_old:
        updates["purchase_date"] = purchase_new.isoformat()
    if expiry != expiry_old:
        updates["expiry_date"] = expiry.isoformat()
    if source != food["source"]:
        updates["source"] = source
    if not updates:
        return food
    return _save(conn, user_id, food, **updates)
