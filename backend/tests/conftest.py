import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.database import get_foods_conn, get_rules_conn, get_today
from app.main import app

# 시험에서만 쓰는 연습용 임시 창고(메모리 DB). 시험이 끝나면 사라진다.
# 실제 식품 DB·규칙표 DB 는 다른 분이 만든다. 칸 이름은 DATA-MODEL.md 를 따랐다 (D-032, D-034).
# 식품 표 이름 "foods" 는 문서에 없어서 가정한 것이다.
FOODS_SCHEMA = """
CREATE TABLE foods (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    storage       TEXT NOT NULL,
    quantity      REAL NOT NULL,
    unit          TEXT NOT NULL,
    purchase_date TEXT NOT NULL,
    expiry_date   TEXT NOT NULL,
    source        TEXT NOT NULL,
    status        TEXT NOT NULL
)
"""

RULES_SCHEMA = [
    """
    CREATE TABLE rules (
        id              TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        default_storage TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE rule_aliases (
        rule_id TEXT NOT NULL,
        alias   TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE rule_storage (
        rule_id  TEXT NOT NULL,
        storage  TEXT NOT NULL,
        allowed  INTEGER NOT NULL,
        max_days INTEGER
    )
    """,
]

TODAY = date(2026, 10, 30)


@pytest.fixture
def today():
    return TODAY


@pytest.fixture
def conn():
    # 서버는 요청마다 다른 스레드를 쓸 수 있어서 check_same_thread=False 로 연다.
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute(FOODS_SCHEMA)
    yield connection
    connection.close()


@pytest.fixture
def rules_conn():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    for statement in RULES_SCHEMA:
        connection.execute(statement)
    yield connection
    connection.close()


def add_rule(rules_conn, name, default_storage, storages, aliases=()):
    """시험용 가짜 규칙표 한 건을 넣는다.

    storages: {"room": (허용 여부, 최대 일수), ...}  값은 시험용 숫자일 뿐이다.
    """
    rule_id = f"rule-{name}"
    rules_conn.execute("INSERT INTO rules VALUES (?, ?, ?)", (rule_id, name, default_storage))
    for alias in aliases:
        rules_conn.execute("INSERT INTO rule_aliases VALUES (?, ?)", (rule_id, alias))
    for storage, (allowed, max_days) in storages.items():
        rules_conn.execute(
            "INSERT INTO rule_storage VALUES (?, ?, ?, ?)",
            (rule_id, storage, 1 if allowed else 0, max_days),
        )
    rules_conn.commit()


@pytest.fixture
def rules(rules_conn):
    """시험용 가짜 규칙표 3건. 실제 규칙표 값이 아니다."""
    add_rule(
        rules_conn,
        "두부",
        "fridge",
        {"room": (False, None), "fridge": (True, 10), "freezer": (True, 30)},
        aliases=("연두부",),
    )
    add_rule(
        rules_conn,
        "당근",
        "fridge",
        {"room": (True, 7), "fridge": (True, 20), "freezer": (True, 60)},
    )
    add_rule(
        rules_conn,
        "우유",
        "fridge",
        {"room": (False, None), "fridge": (True, 7), "freezer": (False, None)},
    )
    return rules_conn


@pytest.fixture
def client(conn, rules, today):
    app.dependency_overrides[get_foods_conn] = lambda: conn
    app.dependency_overrides[get_rules_conn] = lambda: rules
    app.dependency_overrides[get_today] = lambda: today
    yield TestClient(app)
    app.dependency_overrides.clear()
