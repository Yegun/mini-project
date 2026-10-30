"""식품 표 읽기·쓰기. 저장만 하고 규칙 판단(기한 계산, 상태 판정, 검사)은 하지 않는다 (ARCHITECTURE 5절).

- 잘못된 값이 오면 DB 제약이 막고 sqlite3.IntegrityError 가 난다. 쉬운 오류 메시지로 바꾸는 것은 API 몫이다.
- 쓰기 함수는 한 번에 성공하거나, 실패하면 아무것도 바뀌지 않는다 (API-SPEC 3절).
- 없는 식품이나 이미 처리된 식품은 None / False 를 돌려준다. 오류 메시지로 바꾸는 것은 API 몫이다 (D-008).
"""
import sqlite3
import uuid

# update_food 로 고칠 수 있는 칸. id, status 는 여기서 못 바꾼다 (status 는 set_status 로만).
_UPDATABLE = ("name", "storage", "quantity", "unit", "purchase_date", "expiry_date", "source")


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def create_food(
    conn: sqlite3.Connection,
    *,
    name: str,
    storage: str,
    quantity: float,
    unit: str,
    purchase_date: str,
    expiry_date: str,
    source: str,
) -> dict:
    """식품을 만든다. 번호(UUID)는 여기서 만들고, 처리 상태는 none 으로 시작한다."""
    food_id = str(uuid.uuid4())
    with conn:
        conn.execute(
            "INSERT INTO foods (id, name, storage, quantity, unit, purchase_date, expiry_date, source, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'none')",
            (food_id, name, storage, quantity, unit, purchase_date, expiry_date, source),
        )
    return get_food(conn, food_id)


def get_food(conn: sqlite3.Connection, food_id: str, *, include_processed: bool = False) -> dict | None:
    """식품 한 건. 기본은 처리 상태가 none 인 것만 (다 먹음·버림은 없는 것처럼 None)."""
    sql = "SELECT * FROM foods WHERE id = ?"
    if not include_processed:
        sql += " AND status = 'none'"
    return _row(conn.execute(sql, (food_id,)).fetchone())


def list_active_foods(conn: sqlite3.Connection) -> list[dict]:
    """홈 목록용. 처리 상태 none 만, 기한 빠른 순 → 구매일 이른 순 → 이름순 (D-015, D-033)."""
    rows = conn.execute(
        "SELECT * FROM foods WHERE status = 'none' ORDER BY expiry_date, purchase_date, name"
    ).fetchall()
    return [dict(r) for r in rows]


def update_food(conn: sqlite3.Connection, food_id: str, **fields) -> dict | None:
    """처리 전 식품의 칸을 고친다. 없거나 이미 처리됐으면 None. 고칠 칸이 없으면 그대로 돌려준다."""
    unknown = set(fields) - set(_UPDATABLE)
    if unknown:
        raise ValueError(f"고칠 수 없는 칸: {sorted(unknown)}")
    if not fields:
        return get_food(conn, food_id)
    assignments = ", ".join(f"{col} = ?" for col in fields)  # col 은 위에서 거른 고정 이름만
    with conn:
        cur = conn.execute(
            f"UPDATE foods SET {assignments} WHERE id = ? AND status = 'none'",
            (*fields.values(), food_id),
        )
    if cur.rowcount == 0:
        return None
    return get_food(conn, food_id)


def set_status(conn: sqlite3.Connection, food_id: str, status: str) -> dict | None:
    """다 먹음(eaten) / 버림(discarded) 처리. 행은 남긴다. 되돌리기 없음.

    없거나 이미 처리된 식품이면 None. status 가 eaten/discarded 가 아니면 ValueError.
    """
    if status not in ("eaten", "discarded"):
        raise ValueError("status 는 eaten 또는 discarded 만 가능하다")
    with conn:
        cur = conn.execute(
            "UPDATE foods SET status = ? WHERE id = ? AND status = 'none'", (status, food_id)
        )
    if cur.rowcount == 0:
        return None
    return get_food(conn, food_id, include_processed=True)


def delete_food(conn: sqlite3.Connection, food_id: str) -> bool:
    """처리 전 식품의 행을 완전히 지운다. 되돌리기 없음. 없거나 이미 처리됐으면 False."""
    with conn:
        cur = conn.execute("DELETE FROM foods WHERE id = ? AND status = 'none'", (food_id,))
    return cur.rowcount > 0
