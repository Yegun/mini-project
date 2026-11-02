"""시험 도구. DB 시험과 API 시험이 PostgreSQL 임시 schema 를 같이 쓴다.

TEST_DATABASE_URL (.env) 이 없으면 PostgreSQL 이 필요한 시험은 건너뛴다. 운영 표와 섞이지 않게,
시험마다 임시 schema 를 만들고 끝나면 지운다.
"""
import uuid
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.database import get_conn, get_today
from app.main import app

TODAY = date(2026, 10, 30)


@pytest.fixture
def today():
    return TODAY


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


@pytest.fixture
def make_client(pg_rules, today):
    """API 시험용 클라이언트를 만든다. 서버 코드는 시험 DB(임시 schema)에 연결하고, 오늘은 TODAY 로 고정한다.

    클라이언트마다 쿠키 보관함이 따로라서 두 계정(두 기기)을 흉내 낼 수 있다.
    처리 못 한 오류도 500 응답으로 받는다(server_error).
    """
    app.dependency_overrides[get_conn] = lambda: pg_rules
    app.dependency_overrides[get_today] = lambda: today

    def make() -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    yield make
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client):
    return make_client()
