"""사진 읽기 결과(photo_analyses) 읽기·쓰기 (DATA-MODEL 6절, ARCHITECTURE 4-4, D-102, D-133).

- 사진 한 장을 읽은 결과(글만)를 계정마다 한 줄, 30분 동안 잠깐 보관한다. 사진은 저장하지 않는다.
- 새 사진을 올리면 그 계정의 이전 줄을 지우고 새 줄로 바꾼다 (Q-29). 그래서 이전 사진의 번호는 쓸 수 없게 된다.
- 만료(30분)는 읽을 때 판정한다. 만료된 줄을 읽으면 그 줄을 지우고 None 을 돌려주므로,
  부르는 쪽은 None 이어도 commit 해야 지운 것이 남는다 (sessions_repo.check_session 과 같다, Q-14, Q-31).
  로그인할 때도 그 계정의 만료된 줄을 같이 지운다 (sessions_repo.create_session).
- 시각은 DB 시계다 (Q-13). 식품 쪽 "오늘"(get_today)과는 별개다.
- 다른 계정의 번호, 없는 번호, UUID 모양이 아닌 번호는 모두 똑같이 None 이다 (D-063).
- commit 은 하지 않는다.
"""
import uuid

import psycopg
from psycopg.types.json import Jsonb

ANALYSIS_MINUTES = 30


def save_analysis(conn: psycopg.Connection, user_id: str, items: list[dict]) -> str:
    """이 계정의 이전 결과를 지우고 새 결과를 보관한다. 새 번호(analysis_id)를 돌려준다."""
    conn.execute("DELETE FROM photo_analyses WHERE user_id = %s", (user_id,))
    row = conn.execute(
        "INSERT INTO photo_analyses (user_id, items) VALUES (%s, %s) RETURNING id",
        (user_id, Jsonb(items)),
    ).fetchone()
    return str(row["id"])


def get_valid_analysis(conn: psycopg.Connection, user_id: str, analysis_id) -> dict | None:
    """내 결과이고 30분 안이면 {"id", "items", "created_at"}. 아니면 None (analysis_expired).

    30분이 지난 줄이면 그 줄을 지우고 None 을 돌려준다. None 이어도 commit 해야 지운 것이 남는다.
    """
    try:
        wanted = str(uuid.UUID(str(analysis_id)))
    except ValueError:
        return None
    row = conn.execute(
        "SELECT id, items, created_at,"
        " created_at < clock_timestamp() - make_interval(mins => %s) AS expired"
        " FROM photo_analyses WHERE id = %s AND user_id = %s",
        (ANALYSIS_MINUTES, wanted, user_id),
    ).fetchone()
    if row is None:
        return None
    if row["expired"]:
        conn.execute("DELETE FROM photo_analyses WHERE id = %s", (wanted,))
        return None
    return {"id": str(row["id"]), "items": row["items"], "created_at": row["created_at"]}


def delete_analysis(conn: psycopg.Connection, user_id: str, analysis_id) -> bool:
    """쓴 결과를 지운다. 지웠으면 True (한꺼번에 등록이 성공했을 때)."""
    try:
        wanted = str(uuid.UUID(str(analysis_id)))
    except ValueError:
        return False
    return (
        conn.execute(
            "DELETE FROM photo_analyses WHERE id = %s AND user_id = %s", (wanted, user_id)
        ).rowcount
        > 0
    )


def delete_expired(conn: psycopg.Connection, user_id: str) -> int:
    """이 계정의 만료된 결과를 지운다 (로그인할 때). 지운 수를 돌려준다."""
    return conn.execute(
        "DELETE FROM photo_analyses WHERE user_id = %s"
        " AND created_at < clock_timestamp() - make_interval(mins => %s)",
        (user_id, ANALYSIS_MINUTES),
    ).rowcount
