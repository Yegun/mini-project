"""한꺼번에 등록 창구 (API-SPEC 2-5절 F2, US-019, US-020)."""
from typing import Any

from fastapi import APIRouter

from app import bulk
from app.database import transaction
from app.db import photo_analyses_repo
from app.errors import ApiError
from app.routers.common import Body, Conn, Today, UserId
from app.view import food_json

router = APIRouter()


class BulkBody(Body):
    analysis_id: Any = None
    items: Any = None  # 줄마다 item_no, name, quantity, unit, purchase_date, storage (+ expiry_date 또는 expiry_in_days)


@router.post("/foods/bulk", status_code=201)
def create_bulk(body: BulkBody, conn: Conn, user_id: UserId, today: Today):
    """F2 한꺼번에 등록 🔒. 확인 화면에서 남긴 줄을 한 묶음으로 등록한다. 한 줄이라도 실패하면 전부 취소된다 (D-110).

    확인 순서: 로그인 → items 가 비었는지 → 분석 번호(내 것, 30분 안) → 줄마다 검사 → 저장.
    규칙표에 없는 이름의 식품은 서버가 보관한 AI 결과로 규칙표에 더한다 (D-136). 저장하지 않으면 읽기 결과는 남는다.
    """
    raw_items = bulk.check_items(body.items)
    # 읽기 결과 확인은 따로 묶는다. 30분이 지난 줄은 지운 채로 남아야 하기 때문이다 (DATA-MODEL 6절)
    with transaction(conn):
        analysis = photo_analyses_repo.get_valid_analysis(conn, user_id, body.analysis_id)
    if analysis is None:
        raise ApiError("analysis_expired")  # 없음 · 남의 번호 · 30분이 지남을 가르지 않는다 (D-063)
    with transaction(conn):
        plans = bulk.plan_lines(conn, raw_items, analysis, today)
        foods = bulk.apply_plans(conn, user_id, analysis["id"], plans)
    return {"items": [food_json(food, today) for food in foods]}
