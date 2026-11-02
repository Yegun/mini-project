import sqlite3
import uuid
from datetime import date

import psycopg
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


# ---- PostgreSQL 시험 (DB 담당) ----------------------------------------------------------------
# TEST_DATABASE_URL (.env) 이 없으면 PostgreSQL 시험은 건너뛴다. 운영 표와 섞이지 않게,
# 시험마다 임시 schema 를 만들고 끝나면 지운다.
@pytest.fixture
def pg_url():
    from app.db.connection import DatabaseConfigError, env_value

    try:
        return env_value("TEST_DATABASE_URL")
    except DatabaseConfigError:
        pytest.skip("TEST_DATABASE_URL 이 없어 PostgreSQL 시험을 건너뛴다 (.env 에 적는다)")


@pytest.fixture
def pg_schema(pg_url):
    name = "t_" + uuid.uuid4().hex[:12]
    admin = psycopg.connect(pg_url, autocommit=True)
    admin.execute(f'CREATE SCHEMA "{name}"')
    yield name
    admin.execute(f'DROP SCHEMA "{name}" CASCADE')
    admin.close()


@pytest.fixture
def pg(pg_schema):
    """표 7개가 만들어진 빈 임시 schema 에 연결한 psycopg 연결. 저장소 함수처럼 commit 은 시험이 한다."""
    from app.db.connection import connect_test
    from app.db.migrate import apply_migrations

    conn = connect_test(pg_schema)
    apply_migrations(conn)
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def pg_rules(pg):
    """실제 규칙표 30개(seed_rules.py)를 채운 연결."""
    from app.db.seed_rules import seed_rules

    seed_rules(pg)
    pg.commit()
    return pg


@pytest.fixture
def two_users(pg):
    from app.db.users_repo import create_user

    a = create_user(pg, "a@example.com", "Passw0rd!")
    b = create_user(pg, "b@example.com", "Passw0rd!")
    pg.commit()
    return a, b


def food_args(**over):
    data = dict(
        name="양파", storage="room", quantity=2, unit="개",
        purchase_date="2026-10-30", expiry_date="2026-11-29", source="rule",
    )
    data.update(over)
    return data
