"""규칙표 30개 식품 (D-018).

!! 임시값 !!
식품 이름 30개는 확정(D-018)이다. 그 밖의 값(기본 보관 방법, 가능 여부, 최대 보관 일수, 별칭)은
식약처 자료로 확인한 값이 아니라 일반 상식으로 적은 **개발용 임시값**이다.
사용자가 식약처 기준으로 확인해 확정하기 전까지는 기한 숫자를 믿지 않는다.
값을 고친 뒤에는 `python -m app.db.init_db` 를 다시 돌리면 규칙표가 새로 채워진다.

RULES 한 줄: 이름, 기본 보관 방법, {보관 방법: 최대 보관 일수 (None 이면 불가)}, 별칭들
"""
import sqlite3
import uuid

# 규칙표 식품 번호를 이름에서 만든다. 다시 채워도 번호가 같고, 컴퓨터가 달라도 같다.
_NAMESPACE = uuid.UUID("6f1c2b7e-3d5a-4c1e-9a52-0b7d8f4e1a10")

# (이름, 기본, 상온, 냉장, 냉동, 별칭)
RULES: list[tuple[str, str, int | None, int | None, int | None, tuple[str, ...]]] = [
    # 채소 (13)
    ("양파", "room", 30, 60, 180, ()),
    ("대파", "fridge", 3, 14, 60, ()),
    ("감자", "room", 30, 30, None, ()),
    ("당근", "fridge", 5, 21, 120, ()),
    ("양배추", "fridge", 3, 14, 90, ()),
    ("오이", "fridge", 3, 7, None, ()),
    ("상추", "fridge", 1, 5, None, ()),
    ("시금치", "fridge", 1, 5, 90, ()),
    ("마늘", "room", 30, 90, 180, ()),
    ("애호박", "fridge", 3, 7, 90, ("호박",)),
    ("토마토", "room", 5, 10, 90, ()),
    ("배추", "fridge", 3, 14, None, ()),
    ("버섯", "fridge", 1, 7, 60, ()),
    # 과일 (6)
    ("사과", "fridge", 7, 30, None, ()),
    ("바나나", "room", 5, 7, 60, ()),
    ("딸기", "fridge", 1, 5, 180, ()),
    ("귤", "room", 10, 21, None, ("감귤",)),
    ("포도", "fridge", 2, 7, 180, ()),
    ("배", "fridge", 7, 30, None, ()),
    # 육류 (3)
    ("돼지고기", "fridge", None, 3, 180, ()),
    ("소고기", "fridge", None, 3, 180, ("쇠고기",)),
    ("닭고기", "fridge", None, 2, 180, ()),
    # 수산 (4)
    ("고등어", "fridge", None, 2, 90, ()),
    ("오징어", "fridge", None, 2, 90, ()),
    ("새우", "fridge", None, 2, 90, ()),
    ("연어", "fridge", None, 2, 90, ()),
    # 그 밖 (4)
    ("달걀", "fridge", 7, 30, None, ("계란",)),
    ("우유", "fridge", None, 7, None, ()),
    ("두부", "fridge", None, 5, None, ()),
    ("콩나물", "fridge", None, 4, None, ()),
]


def rule_id_for(name: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, name))


def seed_rules(conn: sqlite3.Connection) -> None:
    """규칙표를 비우고 RULES 로 다시 채운다 (한 번에 성공하거나 아무것도 안 바뀐다)."""
    with conn:
        conn.execute("DELETE FROM rule_aliases")
        conn.execute("DELETE FROM rule_storage")
        conn.execute("DELETE FROM rules")
        for name, default, room, fridge, freezer, aliases in RULES:
            days = {"room": room, "fridge": fridge, "freezer": freezer}
            # 기본 보관 방법은 반드시 "가능"한 방법이어야 한다 (DATA-MODEL Q-03)
            if days[default] is None:
                raise ValueError(f"{name}: 기본 보관 방법 {default} 가 불가로 되어 있다")
            rid = rule_id_for(name)
            conn.execute(
                "INSERT INTO rules (id, name, default_storage) VALUES (?, ?, ?)",
                (rid, name, default),
            )
            for storage, max_days in days.items():
                conn.execute(
                    "INSERT INTO rule_storage (rule_id, storage, allowed, max_days) VALUES (?, ?, ?, ?)",
                    (rid, storage, 0 if max_days is None else 1, max_days),
                )
            for alias in aliases:
                conn.execute(
                    "INSERT INTO rule_aliases (rule_id, alias) VALUES (?, ?)", (rid, alias)
                )
