"""로그인 확인 (V-19). 🔒 창구가 모두 같은 이곳에서 로그인 확인을 한다 (D-061).

로그인 상태는 서버가 기억한다. 쿠키 `session` 값으로 sessions 표의 줄을 찾고, 마지막 사용 뒤 30분이 지났으면 거절한다.
- 살아 있으면 마지막 사용 시각을 갱신한다. 갱신은 그 요청의 묶음에 들어 있어서, 요청이 실패해 되돌려지면
  갱신도 되돌려진다 ("요청이 성공할 때마다 갱신", DATA-MODEL 4-2).
- 거절하면(쿠키 없음·없는 줄·30분 지남) 갱신하지 않고 login_required 401 을 낸다. 30분 지난 줄은 지우고,
  그 삭제는 거절 응답 뒤에도 남도록 바로 commit 한다 (끝난 로그인이 되살아나지 않게, API-SPEC 5절 15번).
"""
from typing import Annotated

import psycopg
from fastapi import Depends, Request

from app.database import get_conn
from app.db import sessions_repo
from app.errors import ApiError

COOKIE_NAME = "session"


def session_token(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


def current_user(request: Request, conn: Annotated[psycopg.Connection, Depends(get_conn)]) -> str:
    """로그인한 계정의 번호(user_id). 로그인 상태가 아니면 login_required (401)."""
    try:
        user_id = sessions_repo.check_session(conn, session_token(request))
        if user_id is None:
            conn.commit()  # 거절하면서 지운 줄을 남긴다. 성공했을 때의 갱신은 요청 묶음(transaction)이 마무리한다
    except psycopg.Error as error:
        conn.rollback()
        raise ApiError("server_error") from error
    if user_id is None:
        raise ApiError("login_required")
    return user_id
