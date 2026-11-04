"""식품 창구. 화면의 요청을 받아 검사·계산·저장 담당을 부르고 결과를 돌려준다 (API-SPEC 2-3절, 2-4절의 D3).

경로에 /api 가 없는 이유: 화면의 개발 서버가 /api 를 떼고 넘겨 준다.
모든 창구는 로그인한 계정(UserId)의 식품만 다룬다. 없는 식품·남의 식품·처리된 식품·번호 모양이 틀린 식품은
똑같이 not_found 404 다 (D-008, D-063, D-091). 확인 순서는 로그인 → 내 식품인지 → 입력 검사 → 계산·저장 (API-SPEC 0절).
"""
from typing import Any

from fastapi import APIRouter, Response

from app import services
from app.database import transaction
from app.db import foods_repo
from app.errors import ApiError
from app.routers.common import Body, Conn, Today, UserId
from app.validation import validate_status
from app.view import food_json

router = APIRouter()


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
    category: Any = None  # 식품 종류 (채소·과일·육류·수산·그 밖). 직접 등록은 필수 (V-41)


class UpdateBody(Body):
    # 보낸 칸만 바꾼다. expiry_date 는 "기한을 다시 적어 주세요"를 받은 뒤에만 넣는다.
    name: Any = None
    quantity: Any = None
    unit: Any = None
    purchase_date: Any = None
    expiry_date: Any = None
    storage: Any = None  # 정보 고치기에서 보관 방법도 함께 바꿀 때
    category: Any = None  # 직접 등록 식품의 종류. 규칙표 식품에 보내면 무시한다


class StorageBody(Body):
    storage: Any = None
    expiry_date: Any = None  # 직접 등록 식품은 "기한을 다시 적어 주세요"를 받은 뒤에 넣는다


class ProcessBody(Body):
    status: Any = None


@router.get("/foods")
def list_foods(conn: Conn, user_id: UserId, today: Today):
    """A1 홈 목록 🔒. 내 식품 중 처리 상태가 none 인 것만, 오늘 날짜와 함께 돌려준다 (D-021)."""
    with transaction(conn):
        foods = foods_repo.list_active_foods(conn, user_id)
    return {"today": today.isoformat(), "items": [food_json(food, today) for food in foods]}


@router.post("/foods", status_code=201)
def create_rule_food(body: RuleFoodBody, conn: Conn, user_id: UserId, today: Today):
    """A2 규칙표 식품 등록 🔒."""
    with transaction(conn):
        food = services.register_rule_food(conn, user_id, body.model_dump())
    return food_json(food, today)


@router.post("/foods/manual", status_code=201)
def create_manual_food(body: ManualFoodBody, conn: Conn, user_id: UserId, today: Today):
    """A3 직접 등록 🔒."""
    with transaction(conn):
        food = services.register_manual_food(conn, user_id, body.model_dump(), today)
    return food_json(food, today)


@router.get("/foods/{food_id}")
def get_food(food_id: str, conn: Conn, user_id: UserId, today: Today):
    """A4 식품 상세 🔒. 처리된 식품은 열리지 않는다 (V-20)."""
    with transaction(conn):
        food = foods_repo.get_food(conn, user_id, food_id)
    if food is None:
        raise ApiError("not_found")
    return food_json(food, today)


@router.patch("/foods/{food_id}")
def update_food(food_id: str, body: UpdateBody, conn: Conn, user_id: UserId, today: Today):
    """A5 정보 고치기 🔒 (이름, 구매일, 수량, 단위, 보관 방법, 종류). 보낸 칸만 바꾸고 안 보낸 칸은 그대로다.

    여러 칸이 함께 오면 이름 → 보관 방법 → 구매일 순서로 기한을 다시 계산하고 한 묶음으로 저장한다 (V-39).
    기한을 다시 적어야 하면 409 expiry_required 로 알리고, 이때는 아무것도 저장하지 않는다.
    """
    fields = {name: getattr(body, name) for name in body.model_fields_set}
    with transaction(conn):
        food = foods_repo.get_food(conn, user_id, food_id)
        if food is None:
            raise ApiError("not_found")
        food = services.change_info(conn, user_id, food, fields, today)
    return food_json(food, today)


@router.patch("/foods/{food_id}/storage")
def change_storage(food_id: str, body: StorageBody, conn: Conn, user_id: UserId, today: Today):
    """A6 보관 방법 변경 🔒. 규칙표 식품은 새 기한을 계산하고, 직접 등록 식품은 기한을 다시 적어야 한다."""
    with transaction(conn):
        food = foods_repo.get_food(conn, user_id, food_id)
        if food is None:
            raise ApiError("not_found")
        food = services.change_storage(conn, user_id, food, body.model_dump(), today)
    return food_json(food, today)


@router.patch("/foods/{food_id}/process")
def process_food(food_id: str, body: ProcessBody, conn: Conn, user_id: UserId, today: Today):
    """A7 다 먹음 / 버림 🔒. 처리 상태와 처리한 날짜(서버 한국 시간 오늘)를 저장하고 행은 남긴다 (D-064).

    이미 처리된 식품에 다시 요청하면 not_found 다. 다 먹음을 버림으로 바꾸는 재처리도 안 된다.
    """
    with transaction(conn):
        if foods_repo.get_food(conn, user_id, food_id) is None:  # 식품 확인이 입력 검사보다 먼저다
            raise ApiError("not_found")
        status = validate_status(body.status)
        food = foods_repo.set_status(conn, user_id, food_id, status, today.isoformat())
        if food is None:
            raise ApiError("not_found")
    return food_json(food, today)


@router.patch("/foods/{food_id}/restore")
def restore_food(food_id: str, conn: Conn, user_id: UserId, today: Today):
    """D3 홈으로 되돌리기 🔒. 처리 상태 none, 처리한 날짜 비움. 기한을 다시 계산하지 않는다 (D-075, D-076).

    처리되지 않은 식품·없는 식품·남의 식품은 not_found 다.
    """
    with transaction(conn):
        food = foods_repo.restore_food(conn, user_id, food_id)
    if food is None:
        raise ApiError("not_found")
    return food_json(food, today)


@router.delete("/foods/{food_id}", status_code=204)
def delete_food(food_id: str, conn: Conn, user_id: UserId):
    """A8 삭제 🔒. 행을 완전히 지운다 (기록에도 안 남는다). 처리된 식품은 지울 수 없다 (V-20)."""
    with transaction(conn):
        deleted = foods_repo.delete_food(conn, user_id, food_id)
    if not deleted:
        raise ApiError("not_found")
    return Response(status_code=204)
