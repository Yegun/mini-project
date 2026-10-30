"""식품 창구. 화면의 요청을 받아 검사·계산·저장 담당을 부르고 결과를 돌려준다.

경로에 /api 가 없는 이유: 화면의 개발 서버가 /api 를 떼고 넘겨 준다.
"""

import sqlite3
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from app import repo_foods, services
from app.database import get_foods_conn, get_rules_conn, get_today, transaction
from app.errors import ApiError
from app.status import sort_key
from app.validation import ValidationError
from app.view import food_json

router = APIRouter()

FoodsConn = Annotated[sqlite3.Connection, Depends(get_foods_conn)]
RulesConn = Annotated[sqlite3.Connection, Depends(get_rules_conn)]
Today = Annotated[date, Depends(get_today)]


class Body(BaseModel):
    """요청 본문. 모르는 칸이 있으면 오류. 값 검사는 validation.py 가 직접 한다 (D-010)."""

    model_config = ConfigDict(extra="forbid")


class RuleFoodBody(Body):
    name: Any = None
    quantity: Any = None
    unit: Any = None
    purchase_date: Any = None
    storage: Any = None


class ManualFoodBody(RuleFoodBody):
    # 기한은 날짜로 고르거나(expiry_date), 며칠 뒤인지(expiry_in_days) 적는다. 둘 중 하나만.
    expiry_date: Any = None
    expiry_in_days: Any = None


class UpdateBody(Body):
    # 보낸 칸만 바꾼다. expiry_date 는 "기한을 다시 적어 주세요"를 받은 뒤에만 넣는다.
    name: Any = None
    quantity: Any = None
    unit: Any = None
    purchase_date: Any = None
    expiry_date: Any = None


class StorageBody(Body):
    storage: Any = None
    expiry_date: Any = None  # 직접 등록 식품은 "기한을 다시 적어 주세요"를 받은 뒤에 넣는다


class ProcessBody(Body):
    status: Any = None


def get_active_food(conn: sqlite3.Connection, food_id: str) -> dict:
    """없는 식품, 이미 처리된 식품은 오류로 알린다 (V-14, D-008)."""
    food = repo_foods.get_food(conn, food_id)
    if food is None:
        raise ApiError(404, "not_found")
    if food["status"] != "none":
        raise ApiError(409, "already_processed")
    return food


@router.get("/foods")
def list_foods(conn: FoodsConn, today: Today):
    """A1 홈 목록. 오늘 날짜도 함께 돌려준다 (D-021)."""
    with transaction(conn, "load_failed"):
        foods = repo_foods.list_active_foods(conn)
    foods.sort(key=sort_key)
    return {"today": today.isoformat(), "foods": [food_json(food, today) for food in foods]}


@router.post("/foods", status_code=201)
def create_rule_food(body: RuleFoodBody, conn: FoodsConn, rules_conn: RulesConn, today: Today):
    """A3 규칙표 식품 등록."""
    with transaction(conn):
        food = services.register_rule_food(conn, rules_conn, body.model_dump(), today)
    return food_json(food, today)


@router.post("/foods/manual", status_code=201)
def create_manual_food(body: ManualFoodBody, conn: FoodsConn, today: Today):
    """A4 직접 등록."""
    with transaction(conn):
        food = services.register_manual_food(conn, body.model_dump(), today)
    return food_json(food, today)


@router.get("/foods/{food_id}")
def get_food(food_id: str, conn: FoodsConn, today: Today):
    """A5 식품 상세."""
    with transaction(conn, "load_failed"):
        food = get_active_food(conn, food_id)
    return food_json(food, today)


@router.patch("/foods/{food_id}")
def update_food(
    food_id: str, body: UpdateBody, conn: FoodsConn, rules_conn: RulesConn, today: Today
):
    """A6 정보 수정 (이름, 구매일, 수량, 단위)."""
    fields = {name: getattr(body, name) for name in body.model_fields_set}
    with transaction(conn):
        food = get_active_food(conn, food_id)
        food = services.change_info(conn, rules_conn, food, fields, today)
    return food_json(food, today)


@router.patch("/foods/{food_id}/storage")
def change_storage(
    food_id: str, body: StorageBody, conn: FoodsConn, rules_conn: RulesConn, today: Today
):
    """A7 보관 방법 변경."""
    with transaction(conn):
        food = get_active_food(conn, food_id)
        food = services.change_storage(conn, rules_conn, food, body.model_dump(), today)
    return food_json(food, today)


@router.patch("/foods/{food_id}/process")
def process_food(food_id: str, body: ProcessBody, conn: FoodsConn, today: Today):
    """A8 다 먹음 / 버림. 처리 상태만 바꾸고 행은 남긴다. 되돌리기 없음 (D-013)."""
    if body.status not in ("eaten", "discarded"):
        raise ValidationError("status", "invalid")
    with transaction(conn):
        get_active_food(conn, food_id)
        repo_foods.set_status(conn, food_id, body.status)
        food = repo_foods.get_food(conn, food_id)
    return food_json(food, today)


@router.delete("/foods/{food_id}")
def delete_food(food_id: str, conn: FoodsConn):
    """A9 삭제. 행을 완전히 지운다 (D-013)."""
    with transaction(conn):
        get_active_food(conn, food_id)
        repo_foods.delete_food(conn, food_id)
    return Response(status_code=204)
