"""DB 연결과 요청 단위 묶음, 오늘 날짜.

연결 문자열(.env 의 DATABASE_URL)과 연결 방식은 app/db/connection.py 가 정한다 (한 곳에서만 정한다).
저장소 함수(app/db)는 commit 하지 않으므로, 요청 하나를 한 묶음으로 처리하는 것은 여기 transaction 이다 (OQ-04).
"""
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

import psycopg

from app.db.connection import DatabaseConfigError, connect_app
from app.errors import ApiError

KOREA = ZoneInfo("Asia/Seoul")


def get_conn():
    """요청마다 DB 연결을 새로 열고 끝나면 닫는다. 연결하지 못하면 server_error (US-014)."""
    try:
        conn = connect_app()
    except (psycopg.Error, DatabaseConfigError) as error:
        raise ApiError("server_error") from error
    try:
        yield conn
    finally:
        conn.close()


def get_today() -> date:
    """오늘 날짜. 코드에서 오늘은 여기서만 정한다. 서버 시계를 한국 시간으로 바꾼 날짜다 (D-087, D-088)."""
    return datetime.now(KOREA).date()


@contextmanager
def transaction(conn: psycopg.Connection):
    """요청 하나를 한 묶음으로 처리한다. 중간에 실패하면 전부 되돌려 아무것도 바뀌지 않게 한다.

    DB 쪽 문제는 server_error(500)로 바꿔 알린다. 입력 오류 같은 ApiError·ValidationError 는 되돌리고 그대로 낸다.
    """
    try:
        yield
        conn.commit()
    except psycopg.Error as error:
        _rollback(conn)
        raise ApiError("server_error") from error
    except BaseException:
        _rollback(conn)
        raise


def _rollback(conn: psycopg.Connection) -> None:
    try:
        conn.rollback()
    except psycopg.Error:
        pass
