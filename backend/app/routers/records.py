"""기록 창구 (API-SPEC 2-4절 D1·D2, US-013·US-015). 모두 로그인한 계정의 식품만 센다 (D-061)."""
from datetime import date

from fastapi import APIRouter

from app.database import transaction
from app.db import foods_repo, records_repo
from app.routers.common import Conn, Today, UserId
from app.status import EXPIRED, FRESH, SOON, WARNING, days_left, status_of

router = APIRouter()


@router.get("/records/summary")
def records_summary(conn: Conn, user_id: UserId, today: Today):
    """D1 기록 숫자 🔒. 다섯 가지 숫자를 요청할 때마다 센다. 삭제한 식품은 세지 않는다 (D-070).

    식품 상태별 수는 홈 목록과 같은 판정(status.py)을 쓴다. 달력에서 빠진 지난 지 4일 이상 식품도 지남에 센다.
    다 먹음·버림·현재 식품이 모두 없으면 모든 숫자가 0 이다 (오류가 아니다, D-071).
    """
    with transaction(conn):
        counted = records_repo.records_summary(conn, user_id, today)
    by_status = {FRESH: 0, WARNING: 0, SOON: 0, EXPIRED: 0}
    for expiry in counted["expiry_dates"]:
        by_status[status_of(days_left(date.fromisoformat(expiry), today))] += 1
    return {
        "eaten": counted["eaten"],
        "discarded": counted["discarded"],
        "food_kinds": counted["food_kinds"],
        "by_storage": counted["by_storage"],
        "by_status": by_status,
    }


@router.get("/records/foods")
def processed_foods(conn: Conn, user_id: UserId):
    """D2 처리한 식품 목록 🔒. 다 먹음과 버림을 나눠서, 최근 처리한 순 → 이름순으로 돌려준다 (D-073, D-074)."""
    with transaction(conn):
        return foods_repo.list_processed_foods(conn, user_id)
