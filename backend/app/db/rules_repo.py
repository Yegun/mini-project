"""규칙표 읽기와 '더하기' (D-007, D-133, D-136). 고치거나 지우는 함수는 없다.

앱 DB 계정은 규칙표 세 표에 읽기와 '더하기'만 할 수 있다 (Q-27). 이미 있는 줄을 고치거나 지우는 것과 별칭을 더하는 것은
개발자 계정만 한다. 더하는 일은 add_rule 하나뿐이고, 사진으로 한꺼번에 등록할 때만 부른다.

규칙표 한 건의 모양:
  {"id", "name", "default_storage",
   "storages": [{"storage": "room"|"fridge"|"freezer", "allowed": bool, "max_days": int|None}, ...]}
  storages 는 상온, 냉장, 냉동 순이다. allowed 가 False 면 "불가"이고 max_days 는 None 이다.
이름순은 글자 코드 순으로 고정한다 (Q-23).
"""
import uuid

import psycopg

from app.db.seed_rules import rule_id_for

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
        "SELECT id, name, default_storage, is_danger, danger_note, category FROM rules"
        " WHERE name LIKE %s OR id IN (SELECT rule_id FROM rule_aliases WHERE alias LIKE %s)"
        ' ORDER BY name COLLATE "C"',
        (pattern, pattern),
    ).fetchall()
    return [_with_storages(conn, r) for r in rules]


def get_rule_by_name(conn: psycopg.Connection, name: str) -> dict | None:
    """이름이 정확히 같은 규칙표 식품 (정식 이름만. 별칭은 find_rule 로 찾는다)."""
    row = conn.execute(
        "SELECT id, name, default_storage, is_danger, danger_note, category FROM rules WHERE name = %s", (name,)
    ).fetchone()
    return _with_storages(conn, row) if row else None


def find_rule(conn: psycopg.Connection, name: str) -> dict | None:
    """이름 또는 별칭이 정확히 같은 규칙표 식품. 별칭으로 찾아도 정식 이름의 규칙을 돌려준다 (API-SPEC 5절 20번).

    A2(등록)·A5(이름 수정)가 "규칙표에 있는 이름인가", A3(직접 등록)이 "규칙표에 이미 있는 이름인가"를 판단할 때 쓴다.
    """
    row = conn.execute(
        "SELECT id, name, default_storage, is_danger, danger_note, category FROM rules WHERE name = %s"
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
        "SELECT id, name, default_storage, is_danger, danger_note, category FROM rules WHERE id = %s", (rule_id,)
    ).fetchone()
    return _with_storages(conn, row) if row else None


def add_rule(
    conn: psycopg.Connection,
    name: str,
    default_storage: str,
    storages: list[dict],
    is_danger: bool = False,
    danger_note: str | None = None,
    category: str = "other",
) -> bool:
    """규칙표에 새 식품을 더한다 (한꺼번에 등록 때 규칙표에 같은 이름이 없는 식품, D-136). 더했으면 True.

    storages 는 보관 방법 세 개 [{"storage", "allowed", "max_days"}, ...] 이다. 별칭은 만들지 않는다 (ARCHITECTURE 4-3).
    번호는 이름에서 계산한다 (Q-30). 이미 있는 이름이거나 다른 식품의 별칭이면 아무것도 하지 않고 False 다.
    같은 이름을 두 요청이 동시에 더하려 해도 한 줄만 만들어지고 나중 요청은 영향을 받지 않는다 (먼저 저장된 값이 남는다).
    값 규칙(기본 보관 방법은 "가능", 가능이면 일수가 양수)은 API 가 먼저 검사하고, DB 가 한 번 더 막는다.
    위험 여부·이유·종류는 AI 가 알려 준 값이다. 위험 여부와 이유의 짝, 종류 값은 DB 가 막지 않고 API(V-36)가 지킨다 (Q-36).
    commit 은 하지 않는다.
    """
    if conn.execute("SELECT 1 FROM rule_aliases WHERE alias = %s", (name,)).fetchone():
        return False
    created = conn.execute(
        "INSERT INTO rules (id, name, default_storage, is_danger, danger_note, category)"
        " VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
        (rule_id_for(name), name, default_storage, is_danger, danger_note if is_danger else None, category),
    ).fetchone()
    if created is None:
        return False
    for info in storages:
        conn.execute(
            "INSERT INTO rule_storage (rule_id, storage, allowed, max_days) VALUES (%s, %s, %s, %s)",
            (rule_id_for(name), info["storage"], info["allowed"], info["max_days"]),
        )
    return True


def list_rules(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        'SELECT id, name, default_storage, is_danger, danger_note, category FROM rules ORDER BY name COLLATE "C"'
    ).fetchall()
    return [_with_storages(conn, r) for r in rows]
