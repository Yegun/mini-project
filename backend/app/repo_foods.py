"""식품 DB 를 읽고 쓰는 창고 담당.

- 식품 DB 는 다른 분이 만든다. 여기서는 만들어진 DB 의 식품 표를 오가기만 한다.
- 칸 이름은 DATA-MODEL.md 2절(D-032)을 따른다.
- 저장 확정(commit)과 되돌리기(rollback)는 이 함수를 부르는 쪽이 한다.
  요청 하나가 실패하면 아무것도 바뀌지 않게 하려는 것이다 (OQ-04).
"""

import sqlite3
import uuid
from datetime import date
from decimal import Decimal

# 식품 표 이름. DATA-MODEL.md 에 표 이름이 없어서 가정한 값이다. DB 담당 분과 맞춰야 한다.
FOODS_TABLE = "foods"

_COLUMNS = (
    "id",
    "name",
    "storage",
    "quantity",
    "unit",
    "purchase_date",
    "expiry_date",
    "source",
    "status",
)
# 고칠 수 있는 칸. 번호(id)와 처리 상태(status)는 여기서 바꾸지 못한다.
_UPDATABLE = ("name", "storage", "quantity", "unit", "purchase_date", "expiry_date", "source")
# 처리 상태는 다 먹음 / 버림으로만 바꾼다. 되돌리기는 없다 (D-013).
_PROCESSED = ("eaten", "discarded")

_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM {FOODS_TABLE}"


def _to_food(row: tuple) -> dict:
    food = dict(zip(_COLUMNS, row))
    food["purchase_date"] = date.fromisoformat(food["purchase_date"])
    food["expiry_date"] = date.fromisoformat(food["expiry_date"])
    return food


def _to_db(field: str, value):
    """날짜는 YYYY-MM-DD 글자로, 수량은 숫자로 바꿔서 저장한다 (D-031, D-032)."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def create_food(
    conn: sqlite3.Connection,
    *,
    name: str,
    storage: str,
    quantity,
    unit: str,
    purchase_date: date,
    expiry_date: date,
    source: str,
) -> dict:
    """식품 한 건을 만든다. 번호는 무작위 UUID, 처리 상태는 "none" (D-033)."""
    food_id = str(uuid.uuid4())
    conn.execute(
        f"INSERT INTO {FOODS_TABLE} ({', '.join(_COLUMNS)}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            food_id,
            name,
            storage,
            _to_db("quantity", quantity),
            unit,
            _to_db("purchase_date", purchase_date),
            _to_db("expiry_date", expiry_date),
            source,
            "none",
        ),
    )
    return get_food(conn, food_id)


def get_food(conn: sqlite3.Connection, food_id: str) -> dict | None:
    row = conn.execute(f"{_SELECT} WHERE id = ?", (food_id,)).fetchone()
    return _to_food(row) if row else None


def list_active_foods(conn: sqlite3.Connection) -> list[dict]:
    """처리 상태가 "none" 인 식품만 돌려준다 (A1). 순서는 정하지 않는다. 정렬은 status.py 가 한다."""
    rows = conn.execute(f"{_SELECT} WHERE status = 'none'").fetchall()
    return [_to_food(row) for row in rows]


def update_food(conn: sqlite3.Connection, food_id: str, **fields) -> dict | None:
    """정해진 칸만 고친다. 없는 식품이면 None."""
    unknown = set(fields) - set(_UPDATABLE)
    if unknown:
        raise ValueError(f"cannot update: {sorted(unknown)}")
    if fields:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = [_to_db(name, value) for name, value in fields.items()]
        conn.execute(
            f"UPDATE {FOODS_TABLE} SET {assignments} WHERE id = ?", (*values, food_id)
        )
    return get_food(conn, food_id)


def set_status(conn: sqlite3.Connection, food_id: str, status: str) -> bool:
    """처리 상태를 다 먹음 / 버림으로 바꾼다. 행은 남긴다. 없는 식품이면 False."""
    if status not in _PROCESSED:
        raise ValueError(f"status must be one of {_PROCESSED}")
    cursor = conn.execute(
        f"UPDATE {FOODS_TABLE} SET status = ? WHERE id = ?", (status, food_id)
    )
    return cursor.rowcount > 0


def delete_food(conn: sqlite3.Connection, food_id: str) -> bool:
    """행을 완전히 지운다. 없는 식품이면 False."""
    cursor = conn.execute(f"DELETE FROM {FOODS_TABLE} WHERE id = ?", (food_id,))
    return cursor.rowcount > 0
