"""식품을 만들고 고치는 규칙을 한 곳에 모았다 (검사 → 기한 계산 → 저장).

창구(routers)는 요청을 받아 여기로 넘기기만 하고, 저장 확정(commit)은 창구가 transaction 으로 한다.
저장소(app/db)는 저장만 한다. 검사·기한 계산·규칙표 판단은 여기서 한다 (ARCHITECTURE 5절).
"""
from datetime import date

import psycopg

from app.calc import expiry_from_days
from app.db import foods_repo, rules_repo
from app.errors import ApiError
from app.validation import (
    ValidationError,
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
    """그 보관 방법의 최대 보관 기간(일). 허용된 방법인데 기간이 비어 있으면 규칙표가 잘못된 것이다."""
    for info in rule["storages"]:
        if info["storage"] == storage and info["max_days"] is not None:
            return info["max_days"]
    raise ApiError("server_error")


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
