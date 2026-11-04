"""한꺼번에 등록 규칙 (API-SPEC 2-5절 F2, ARCHITECTURE V-24 ~ V-26, D-108 ~ D-111, D-133 ~ D-136).

사진으로 읽은 식품 여러 개를 한 묶음으로 등록한다. 한 줄이라도 실패하면 전부 취소되어 아무것도 등록되지 않고 규칙표에도
더해지지 않는다 (D-110, D-136). 규칙표에 더하는 값은 화면이 보낸 값이 아니라 서버가 보관한 AI 결과에서만 가져온다 (V-26).

확인 순서 (API-SPEC F2): 요청 전체(items 가 비었음 → analysis_id) → 줄 순서대로 →
한 줄 안에서는 줄 번호, 이름, 단위, 수량, 구매일, 보관 방법, 기한 순이다. 첫 오류 하나만 돌려준다.
"""
from datetime import date

import psycopg

from app.calc import expiry_from_days
from app.db import foods_repo, photo_analyses_repo, rules_repo
from app.errors import ApiError
from app.services import allowed_storages, rule_max_days
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


def check_items(raw_items) -> list:
    """items 가 비었거나 목록이 아니면 required (API-SPEC 5절 33번). 화면은 등록 버튼을 막지만 API 도 막는다 (D-010)."""
    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError("items", "required")
    return raw_items


def _read_item_no(raw, position: int, saved: dict[int, dict], seen: set[int]) -> dict:
    """보낸 줄이 가리키는, 서버가 보관한 읽기 결과의 줄을 찾는다. 없거나 두 번 나오면 invalid_item (API-SPEC 5절 32번)."""
    field = f"items.{position}.item_no"
    number = raw.get("item_no") if isinstance(raw, dict) else None
    if isinstance(number, bool) or not isinstance(number, int) or number not in saved or number in seen:
        raise ApiError("invalid_item", field)
    seen.add(number)
    return saved[number]


def _plan_line(conn: psycopg.Connection, raw: dict, read: dict, today: date) -> dict:
    """한 줄을 검사하고 저장할 값과 (있으면) 규칙표에 더할 값을 정한다. 줄 번호는 이미 확인했다.

    줄 종류 (API-SPEC F2):
      규칙표에 같은 이름이 있음(읽은 이름 그대로든 고친 이름이든) → 규칙표 값으로 기한 계산, 규칙표 식품(rule)
      읽은 이름 그대로이고 규칙표에 없음 → 서버가 보관한 AI 값으로 기한 계산, 규칙표에 더함, 규칙표 식품(rule)
      이름을 고쳤고 규칙표에 없음 → 규칙표에 더하지 않고 사용자가 적은 기한으로 직접 등록 식품(manual)
    """
    name = validate_text(raw.get("name"), "name")
    unit = validate_text(raw.get("unit"), "unit")
    quantity = validate_quantity(raw.get("quantity"))
    purchase_date = parse_date(raw.get("purchase_date"), "purchase_date")
    storage = validate_storage(raw.get("storage"))

    plan = {"unit": unit, "quantity": quantity, "purchase_date": purchase_date, "storage": storage, "add_rule": None}
    rule = rules_repo.find_rule(conn, name)  # 이름 또는 별칭이 글자 그대로 같을 때 (D-035, D-135)
    if rule is not None:
        validate_storage_allowed(storage, allowed_storages(rule))
        expiry = expiry_from_days(purchase_date, rule_max_days(rule, storage))
        check_purchase_not_after_expiry(purchase_date, expiry)
        plan.update(name=rule["name"], expiry_date=expiry, source="rule")  # 별칭으로 보내도 저장되는 이름은 정식 이름
    elif name == read["name"]:
        by_storage = {info["storage"]: info for info in read["storages"]}
        validate_storage_allowed(storage, {s for s, info in by_storage.items() if info["allowed"]})
        expiry = expiry_from_days(purchase_date, by_storage[storage]["max_days"])
        check_purchase_not_after_expiry(purchase_date, expiry)
        plan.update(
            name=name,
            expiry_date=expiry,
            source="rule",
            add_rule={
                "name": name,
                "default_storage": read["recommended_storage"],
                "storages": read["storages"],
                # 위험 여부·이유·종류도 서버가 보관한 AI 결과에서만 가져온다 (V-26, V-36, D-165).
                # 이 버전 이전에 보관된 결과(30분 안)에는 칸이 없을 수 있어 위험 아님, other 로 둔다.
                "is_danger": bool(read.get("is_danger", False)),
                "danger_note": read.get("danger_note"),
                "category": read.get("category") or "other",
            },
        )
    else:
        expiry = resolve_manual_expiry(purchase_date, raw.get("expiry_date"), raw.get("expiry_in_days"), today)
        # 종류는 서버가 보관한 읽기 결과에서 가져온다. 화면이 보낸 값은 쓰지 않는다 (API-SPEC 5절 50번)
        plan.update(name=name, expiry_date=expiry, source="manual", category=read.get("category") or "other")
    return plan


def plan_lines(conn: psycopg.Connection, raw_items: list, analysis: dict, today: date) -> list[dict]:
    """모든 줄을 순서대로 검사한다. 첫 오류에서 멈추고 오류의 칸 이름에 줄 위치(items.N.)를 붙인다 (API-SPEC 5절 21, 27번)."""
    saved = {item["item_no"]: item for item in analysis["items"]}
    seen: set[int] = set()
    plans = []
    for position, raw in enumerate(raw_items):
        read = _read_item_no(raw, position, saved, seen)
        try:
            plans.append(_plan_line(conn, raw, read, today))
        except ValidationError as error:
            raise ValidationError(f"items.{position}.{error.field}", error.reason) from error
    return plans


def apply_plans(conn: psycopg.Connection, user_id: str, analysis_id: str, plans: list[dict]) -> list[dict]:
    """검사를 마친 줄을 한 묶음 안에서 저장한다: 규칙표 더하기 → 식품 저장 → 쓴 읽기 결과 지우기 (부르는 쪽이 transaction).

    읽기 결과를 지우지 못하면(다른 요청이 먼저 썼다) analysis_expired 로 전부 되돌린다. 같은 요청이 두 번 와도 한 번만 등록된다.
    """
    for plan in plans:
        if plan["add_rule"] is not None:
            rules_repo.add_rule(conn, **plan["add_rule"])  # 이미 있으면 건드리지 않는다 (D-135)
    foods = [
        foods_repo.create_food(
            conn,
            user_id,
            name=plan["name"],
            storage=plan["storage"],
            quantity=plan["quantity"],
            unit=plan["unit"],
            purchase_date=plan["purchase_date"].isoformat(),
            expiry_date=plan["expiry_date"].isoformat(),
            source=plan["source"],
            category=plan.get("category"),
        )
        for plan in plans
    ]
    if not photo_analyses_repo.delete_analysis(conn, user_id, analysis_id):
        raise ApiError("analysis_expired")
    return foods
