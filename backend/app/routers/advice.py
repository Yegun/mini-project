"""기록 조언 창구 (API-SPEC 2-9절 I1, US-034). 저장하지 않는다 (D-161)."""
from fastapi import APIRouter

from app import advice
from app.database import transaction
from app.db import foods_repo
from app.routers.common import Conn, Today, UserId

router = APIRouter()


@router.post("/advice")
def give_advice(conn: Conn, user_id: UserId, today: Today):
    """I1 기록 조언 🔒. 내 식품(처리 전 + 처리한 것)을 AI 에게 보내 기록과 지금 상태를 함께 본 조언을 받는다.

    확인 순서는 로그인 → 식품 읽기 → AI 다 (API-SPEC 0절). 식품도 기록도 없으면 AI 를 부르지 않고 no_data 다 (실패가 아니다).
    DB 연결은 식품을 읽은 뒤 AI 를 기다리는 동안 열린 묶음 없이 두고, AI 답은 DB 에 쓰지 않는다.
    """
    with transaction(conn):
        active = foods_repo.list_active_foods(conn, user_id)
        processed = foods_repo.list_processed_for_advice(conn, user_id, advice.PROCESSED_LIMIT)
    return advice.advise(active, processed, today)
