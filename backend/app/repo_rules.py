"""규칙표 DB 를 읽기만 하는 담당 (D-007, D-034).

규칙표는 개발자만 고치고, 앱은 읽기만 한다. 그래서 이 파일에는 쓰기 함수가 없다.
표 이름과 칸 이름은 DATA-MODEL.md 4절을 따른다: rules, rule_aliases, rule_storage.
"""

import sqlite3
from collections import defaultdict

STORAGE_ORDER = ("room", "fridge", "freezer")


def list_rules(conn: sqlite3.Connection) -> list[dict]:
    """규칙표 전체를 이름순으로 돌려준다 (30개뿐이라 한 번에 읽는다).

    규칙 하나: {"id", "name", "default_storage", "aliases": [...],
                "storages": {"room": {"allowed": bool, "max_days": int|None}, ...}}
    """
    aliases = defaultdict(list)
    for rule_id, alias in conn.execute("SELECT rule_id, alias FROM rule_aliases ORDER BY alias"):
        aliases[rule_id].append(alias)

    storages = defaultdict(dict)
    for rule_id, storage, allowed, max_days in conn.execute(
        "SELECT rule_id, storage, allowed, max_days FROM rule_storage"
    ):
        storages[rule_id][storage] = {"allowed": bool(allowed), "max_days": max_days}

    rules = []
    for rule_id, name, default_storage in conn.execute(
        "SELECT id, name, default_storage FROM rules ORDER BY name"
    ):
        rules.append(
            {
                "id": rule_id,
                "name": name,
                "default_storage": default_storage,
                "aliases": aliases[rule_id],
                "storages": storages[rule_id],
            }
        )
    return rules


def find_rule_by_name(conn: sqlite3.Connection, name: str) -> dict | None:
    """규칙표에 있는 이름과 글자가 똑같은 식품을 찾는다. 별칭은 이름이 아니다."""
    for rule in list_rules(conn):
        if rule["name"] == name:
            return rule
    return None


def allowed_storages(rule: dict) -> set[str]:
    return {storage for storage, info in rule["storages"].items() if info["allowed"]}


def not_allowed_storages(rule: dict) -> list[str]:
    """고를 수 없는("불가") 보관 방법. 상온·냉장·냉동 순서."""
    allowed = allowed_storages(rule)
    return [storage for storage in STORAGE_ORDER if storage not in allowed]


def max_days(rule: dict, storage: str) -> int | None:
    """그 보관 방법의 최대 보관 기간(일). 불가한 방법이면 None."""
    info = rule["storages"].get(storage)
    return info["max_days"] if info else None
