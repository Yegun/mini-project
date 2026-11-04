"""오늘의 일반 조언(daily_tips) 읽기·쓰기 (DATA-MODEL 6-1, ARCHITECTURE 4-6, D-156, D-157).

- 한국 시간 하루에 한 줄, 그날의 조언 글 목록이다. 모든 계정이 같은 줄을 읽는다. 주인(계정) 칸이 없다.
- 날짜는 DB 시계가 아니라 API 의 get_today() 를 인자로 받는다 (D-088).
- 앱 DB 계정은 이 표에 읽기와 '더하기'만 한다. 있는 줄을 고치거나 지우지 않는다. 오래된 날짜도 지우지 않는다.
- 같은 날 요청 두 개가 동시에 와서 둘 다 만들려 하면 먼저 저장된 줄이 남고 나중 요청은 영향을 받지 않는다.
- commit 은 하지 않는다.
"""
from datetime import date

import psycopg
from psycopg.types.json import Jsonb


def get_tips(conn: psycopg.Connection, tip_date: date) -> list[str] | None:
    """그날의 조언 글 목록. 저장된 줄이 없으면 None."""
    row = conn.execute("SELECT tips FROM daily_tips WHERE tip_date = %s", (tip_date,)).fetchone()
    return list(row["tips"]) if row else None


def add_tips(conn: psycopg.Connection, tip_date: date, tips: list[str]) -> bool:
    """그날의 조언을 더한다. 더했으면 True. 이미 그날의 줄이 있으면 아무것도 하지 않고 False (먼저 저장된 것이 남는다)."""
    created = conn.execute(
        "INSERT INTO daily_tips (tip_date, tips) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING tip_date",
        (tip_date, Jsonb(tips)),
    ).fetchone()
    return created is not None
