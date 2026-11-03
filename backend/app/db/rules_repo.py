"""규칙표 읽기 전용 (D-007). 쓰는 함수는 없다. 앱 DB 계정은 규칙표를 쓸 수 없다 (Q-16).

규칙표 한 건의 모양:
  {"id", "name", "default_storage",
   "storages": [{"storage": "room"|"fridge"|"freezer", "allowed": bool, "max_days": int|None}, ...]}
  storages 는 상온, 냉장, 냉동 순이다. allowed 가 False 면 "불가"이고 max_days 는 None 이다.
이름순은 글자 코드 순으로 고정한다 (Q-23).
"""
import uuid

import psycopg

_STORAGE_ORDER = "CASE storage WHEN 'room' THEN 0 WHEN 'fridge' THEN 1 ELSE 2 END"


def _with_storages(conn: psycopg.Connection, rule: dict) -> dict:
    rows = conn.execute(
        f"SELECT storage, allowed, max_days FROM rule_storage WHERE rule_id = %s ORDER BY {_STORAGE_ORDER}",
        (rule["id"],),
    ).fetchall()
    result = dict(rule)
    result["id"] = str(result["id"])
    result["storages"] = [
        {"storage": r["storage"], "allowed": r["allowed"], "max_days": r["max_days"]} for r in rows
    ]
    return result


def search_rules(conn: psycopg.Connection, q: str) -> list[dict]:
    """이름이나 별칭에 검색어가 들어 있는 식품을 이름순으로 돌려준다 (오타 보정 없음, PRD 4-3).

    검색어가 비면 빈 목록. 별칭으로 찾아도 결과에는 식품 이름이 나오고 같은 식품은 한 번만 나온다.
    검색어의 % 와 _ 는 글자 그대로 찾는다.
    """
    q = q.strip()
    if not q:
        return []
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    rules = conn.execute(
        "SELECT id, name, default_storage FROM rules"
        " WHERE name LIKE %s OR id IN (SELECT rule_id FROM rule_aliases WHERE alias LIKE %s)"
        ' ORDER BY name COLLATE "C"',
        (pattern, pattern),
    ).fetchall()
    return [_with_storages(conn, r) for r in rules]


def get_rule_by_name(conn: psycopg.Connection, name: str) -> dict | None:
    """이름이 정확히 같은 규칙표 식품 (정식 이름만. 별칭은 find_rule 로 찾는다)."""
    row = conn.execute(
        "SELECT id, name, default_storage FROM rules WHERE name = %s", (name,)
    ).fetchone()
    return _with_storages(conn, row) if row else None


def find_rule(conn: psycopg.Connection, name: str) -> dict | None:
    """이름 또는 별칭이 정확히 같은 규칙표 식품. 별칭으로 찾아도 정식 이름의 규칙을 돌려준다 (API-SPEC 5절 20번).

    A2(등록)·A5(이름 수정)가 "규칙표에 있는 이름인가", A3(직접 등록)이 "규칙표에 이미 있는 이름인가"를 판단할 때 쓴다.
    """
    row = conn.execute(
        "SELECT id, name, default_storage FROM rules WHERE name = %s"
        " OR id IN (SELECT rule_id FROM rule_aliases WHERE alias = %s)",
        (name, name),
    ).fetchone()
    return _with_storages(conn, row) if row else None


def get_rule(conn: psycopg.Connection, rule_id: str) -> dict | None:
    try:
        rule_id = str(uuid.UUID(str(rule_id)))
    except ValueError:
        return None  # 번호 모양이 UUID 가 아니다. 없는 것으로 본다.
    row = conn.execute(
        "SELECT id, name, default_storage FROM rules WHERE id = %s", (rule_id,)
    ).fetchone()
    return _with_storages(conn, row) if row else None


def list_rules(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        'SELECT id, name, default_storage FROM rules ORDER BY name COLLATE "C"'
    ).fetchall()
    return [_with_storages(conn, r) for r in rows]
