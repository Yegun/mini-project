"""로그인 상태(sessions) 읽기·쓰기 (US-012, D-052 ~ D-054, D-095).

- 기기 한 대 = 한 줄. 한 기기의 로그아웃은 그 줄만 지운다.
- 쿠키 `session` 에는 긴 무작위 값을 담고, DB 에는 그 값의 해시(sha256)만 저장한다 (Q-12).
- 마지막 사용 시각은 DB 시계다 (Q-13). 30분이 지나면 끝난다. 식품 쪽 "오늘"(get_today)과는 별개다.
- 만료된 줄은 만료된 요청을 거절할 때, 그리고 로그인할 때 그 계정 것을 지운다 (Q-14). 별도 정리 작업은 없다.
- commit 은 하지 않는다. 단, 만료된 요청을 거절하면서 지운 줄은 거절 응답 뒤에도 남아야 하므로
  부르는 쪽이 check_session 이 None 을 돌려줘도 commit 해야 한다.
"""
import hashlib
import secrets

import psycopg

from app.db import photo_analyses_repo

SESSION_MINUTES = 30


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(conn: psycopg.Connection, user_id: str) -> str:
    """이 기기의 로그인 상태를 새로 만들고 쿠키에 담을 값(원문)을 돌려준다.

    그 계정의 만료된 로그인 상태와 만료된 사진 읽기 결과도 같이 지운다 (Q-14, Q-31).
    """
    conn.execute(
        "DELETE FROM sessions WHERE user_id = %s AND last_used_at < clock_timestamp() - make_interval(mins => %s)",
        (user_id, SESSION_MINUTES),
    )
    photo_analyses_repo.delete_expired(conn, user_id)
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (id, user_id) VALUES (%s, %s)", (_hash(token), user_id))
    return token


def check_session(conn: psycopg.Connection, token: str | None) -> str | None:
    """쿠키 값이 살아 있는 로그인 상태면 마지막 사용 시각을 갱신하고 계정 번호(user_id)를 돌려준다.

    쿠키가 없거나, 줄이 없거나, 30분이 지났으면 None (login_required). 30분이 지난 줄은 갱신하지 않고 지운다 (V-19).
    """
    if not token:
        return None
    token_hash = _hash(token)
    row = conn.execute(
        "UPDATE sessions SET last_used_at = clock_timestamp()"
        " WHERE id = %s AND last_used_at >= clock_timestamp() - make_interval(mins => %s) RETURNING user_id",
        (token_hash, SESSION_MINUTES),
    ).fetchone()
    if row is not None:
        return str(row["user_id"])
    conn.execute("DELETE FROM sessions WHERE id = %s", (token_hash,))  # 만료된 줄이면 지운다
    return None


def delete_session(conn: psycopg.Connection, token: str | None) -> bool:
    """로그아웃. 이 기기의 줄 하나만 지운다. 지웠으면 True (D-054)."""
    if not token:
        return False
    return conn.execute("DELETE FROM sessions WHERE id = %s", (_hash(token),)).rowcount > 0
