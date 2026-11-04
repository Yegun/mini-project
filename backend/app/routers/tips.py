"""오늘의 일반 조언 창구 (API-SPEC 2-10절 J1, US-033, US-043). 모든 계정이 같은 조언을 읽는다 (D-156)."""
from fastapi import APIRouter

from app import tips
from app.database import transaction
from app.db import tips_repo
from app.routers.common import Conn, Today, UserId

router = APIRouter()


@router.get("/tips")
def todays_tips(conn: Conn, user_id: UserId, today: Today):
    """J1 오늘의 일반 조언 🔒. 오늘(한국 시간) 것이 저장돼 있으면 그대로, 없으면 이 요청이 AI 에게 만들게 해 저장한다.

    AI 가 못 만들거나 맞는 문장이 하나도 안 남으면 저장하지 않고 미리 써 둔 조언을 돌려준다(from_ai 거짓, ai_failed 를 주지 않는다).
    저장된 조언을 읽지 못하거나 저장하지 못하면 server_error 다. 로그인 확인은 하지만 조언은 계정과 상관없다.
    AI 를 기다리는 동안에는 DB 묶음을 열어 두지 않는다.
    """
    with transaction(conn):
        saved = tips_repo.get_tips(conn, today)
    if saved is not None:
        return tips.body(today, saved, from_ai=True)

    made = tips.make_tips()  # 못 만들면 None
    if made is None:
        return tips.fallback_body(today)  # 저장하지 않는다. 다음 요청에서 다시 만들어 본다 (D-157)

    with transaction(conn):
        tips_repo.add_tips(conn, today, made)  # 동시에 만든 요청이 있으면 먼저 저장된 줄이 남는다
        stored = tips_repo.get_tips(conn, today)
    return tips.body(today, stored if stored is not None else made, from_ai=True)
