"""음식 추천 창구 (API-SPEC 2-6절 G1, US-021)."""
from typing import Any

from fastapi import APIRouter

from app import recommend
from app.database import transaction
from app.db import foods_repo
from app.routers.common import Body, Conn, Today, UserId

router = APIRouter()


class RecommendBody(Body):
    meal: Any = None
    cuisine: Any = None
    cuisine_text: Any = None  # cuisine 이 custom 일 때만 쓰고, 아니면 무시한다


@router.post("/recommendations")
def recommendations(body: RecommendBody, conn: Conn, user_id: UserId, today: Today):
    """G1 음식 추천 🔒. 내 식품(처리 전, 지남 아님)으로 만들 수 있는 음식을 AI 에게 묻는다. 저장하지 않는다 (D-122).

    확인 순서는 로그인 → 입력 검사 → 식품 읽기 → AI 다 (API-SPEC 0절). 가진 식품이 없으면 AI 를 부르지 않는다.
    DB 연결은 식품을 읽은 뒤 AI 를 기다리는 동안 열린 묶음 없이 두고, AI 답은 DB 에 쓰지 않는다.
    """
    raw = body.model_dump()
    recommend.validate_request(raw)  # AI 를 부르기 전에 입력부터 막는다 (식품을 읽기 전에도 같은 결과)
    with transaction(conn):
        foods = foods_repo.list_active_foods(conn, user_id)
    return recommend.recommend(raw, foods, today)
