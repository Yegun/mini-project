"""창고(DB)에 연결하는 곳.

식품 DB 와 규칙표 DB 는 다른 분이 만든다. 여기서는 만들어진 파일에 연결만 한다.
파일 위치는 아래 환경 변수로 바꿀 수 있고, 없으면 backend/data/ 안의 기본 이름을 쓴다.
(위치와 이름은 DB 담당 분과 맞춰야 하는 가정이다)
  FOODS_DB_PATH  식품 DB   (기본 backend/data/foods.db)
  RULES_DB_PATH  규칙표 DB (기본 backend/data/rules.db)
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from app.errors import ApiError

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _db_path(env_name: str, default_name: str) -> Path:
    return Path(os.environ.get(env_name) or _DATA_DIR / default_name)


def _connect(path: Path, mode: str) -> sqlite3.Connection:
    """mode: "rw" 는 읽기·쓰기, "ro" 는 읽기 전용. 파일이 없으면 새로 만들지 않고 실패한다."""
    try:
        return sqlite3.connect(
            f"{path.resolve().as_uri()}?mode={mode}", uri=True, check_same_thread=False
        )
    except sqlite3.Error as error:
        raise ApiError(500, "load_failed") from error


def get_foods_conn():
    conn = _connect(_db_path("FOODS_DB_PATH", "foods.db"), "rw")
    try:
        yield conn
    finally:
        conn.close()


def get_rules_conn():
    """규칙표는 앱이 읽기만 한다 (D-007). 그래서 읽기 전용으로 연다."""
    conn = _connect(_db_path("RULES_DB_PATH", "rules.db"), "ro")
    try:
        yield conn
    finally:
        conn.close()


def get_today() -> date:
    """오늘 날짜는 이 컴퓨터(API)의 시계 하나만 쓴다 (D-009)."""
    return date.today()


def _rollback(conn: sqlite3.Connection) -> None:
    try:
        conn.rollback()
    except sqlite3.Error:
        pass


@contextmanager
def transaction(conn: sqlite3.Connection, failure: str = "save_failed"):
    """요청 하나를 한 묶음으로 처리한다. 중간에 실패하면 전부 되돌려 아무것도 바뀌지 않게 한다 (OQ-04).

    창고 쪽 문제는 failure 이유(저장 실패 / 불러오기 실패)의 500 오류로 바꿔 알린다.
    """
    try:
        yield
        conn.commit()
    except sqlite3.Error as error:
        _rollback(conn)
        raise ApiError(500, failure) from error
    except BaseException:
        _rollback(conn)
        raise
