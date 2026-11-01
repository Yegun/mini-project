"""규칙표 읽기 전용 (D-007). 쓰는 함수는 없다.

규칙표 한 건의 모양:
  {"id", "name", "default_storage",
   "storages": [{"storage": "room"|"fridge"|"freezer", "allowed": bool, "max_days": int|None}, ...]}
  storages 는 상온, 냉장, 냉동 순이다. allowed 가 False 면 "불가"이고 max_days 는 None 이다.
"""
import sqlite3

_STORAGE_ORDER = "CASE storage WHEN 'room' THEN 0 WHEN 'fridge' THEN 1 ELSE 2 END"


def _with_storages(conn: sqlite3.Connection, rule: sqlite3.Row) -> dict:
    rows = conn.execute(
        f"SELECT storage, allowed, max_days FROM rule_storage WHERE rule_id = ? ORDER BY {_STORAGE_ORDER}",
        (rule["id"],),
    ).fetchall()
    result = dict(rule)
    result["storages"] = [
        {"storage": r["storage"], "allowed": bool(r["allowed"]), "max_days": r["max_days"]} for r in rows
    ]
    return result


def search_rules(conn: sqlite3.Connection, q: str) -> list[dict]:
    """이름이나 별칭에 검색어가 들어 있는 식품을 이름순으로 돌려준다 (오타 보정 없음, PRD 4-3).

    검색어가 비면 빈 목록. 별칭으로 찾아도 결과에는 식품 이름이 나오고 같은 식품은 한 번만 나온다.
    """
    q = q.strip()
    if not q:
        return []
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    rules = conn.execute(
        "SELECT * FROM rules WHERE name LIKE ? ESCAPE '\\'"
        " OR id IN (SELECT rule_id FROM rule_aliases WHERE alias LIKE ? ESCAPE '\\')"
        " ORDER BY name",
        (pattern, pattern),
    ).fetchall()
    return [_with_storages(conn, r) for r in rules]


def get_rule_by_name(conn: sqlite3.Connection, name: str) -> dict | None:
    """이름이 정확히 같은 규칙표 식품. "규칙표에 있는 이름인가" 판단에 쓴다 (A6)."""
    row = conn.execute("SELECT * FROM rules WHERE name = ?", (name,)).fetchone()
    return _with_storages(conn, row) if row else None


def get_rule(conn: sqlite3.Connection, rule_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    return _with_storages(conn, row) if row else None


def list_rules(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM rules ORDER BY name").fetchall()
    return [_with_storages(conn, r) for r in rows]
