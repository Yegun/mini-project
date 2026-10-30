"""식품 저장 담당. DB 담당이 만든 app/db/foods_repo 를 부르는 창구다.

DB 에는 날짜가 `YYYY-MM-DD` 글자로, 수량이 숫자로 저장된다 (D-031, D-032).
API 안에서는 날짜를 날짜 값으로 다루므로, 여기서 서로 바꿔 준다. 그 밖의 일은 하지 않는다.
처리된 식품(다 먹음·버림)은 조회·수정·삭제가 막혀 있고, 없는 식품과 똑같이 None / False 다 (D-037).
저장 확정(commit)과 되돌리기(rollback)는 부르는 쪽(routers)이 transaction 으로 한다 (OQ-04).
"""

import sqlite3
from datetime import date
from decimal import Decimal

from app.db import foods_repo


def _to_food(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        **row,
        "purchase_date": date.fromisoformat(row["purchase_date"]),
        "expiry_date": date.fromisoformat(row["expiry_date"]),
    }


def _to_db(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def create_food(conn: sqlite3.Connection, **fields) -> dict:
    return _to_food(foods_repo.create_food(conn, **{k: _to_db(v) for k, v in fields.items()}))


def get_food(conn: sqlite3.Connection, food_id: str, *, include_processed: bool = False) -> dict | None:
    return _to_food(foods_repo.get_food(conn, food_id, include_processed=include_processed))


def list_active_foods(conn: sqlite3.Connection) -> list[dict]:
    """처리 전 식품. 기한 → 구매일 → 이름순은 저장소가 정한다 (D-015, D-033)."""
    return [_to_food(row) for row in foods_repo.list_active_foods(conn)]


def update_food(conn: sqlite3.Connection, food_id: str, **fields) -> dict | None:
    return _to_food(foods_repo.update_food(conn, food_id, **{k: _to_db(v) for k, v in fields.items()}))


def set_status(conn: sqlite3.Connection, food_id: str, status: str) -> dict | None:
    return _to_food(foods_repo.set_status(conn, food_id, status))


def delete_food(conn: sqlite3.Connection, food_id: str) -> bool:
    return foods_repo.delete_food(conn, food_id)
