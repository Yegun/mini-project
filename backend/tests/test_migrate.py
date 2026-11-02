"""표 만들기·되돌리기 (알렘빅 + PostgreSQL). 7개 표, 여러 번 실행해도 안전, 되돌리기, 중간에 실패하면 아무것도 안 바뀜."""
import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.db.connection import BACKEND_DIR, connect_test
from app.db.migrate import alembic_config, downgrade, upgrade

TABLES = {"users", "sessions", "foods", "rules", "rule_aliases", "rule_storage", "legacy_migration"}
VERSIONS = sorted(p.name for p in (BACKEND_DIR / "alembic" / "versions").glob("0*.py"))


def tables(conn):
    rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")
    return {r["table_name"] for r in rows}


def version(conn):
    row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    conn.rollback()
    return row["version_num"] if row else None


def test_creates_the_seven_tables(pg):
    assert TABLES <= tables(pg)
    assert version(pg) == "0002"


def test_foods_has_owner_and_processed_date_columns(pg):
    cols = {
        r["column_name"]: r["data_type"]
        for r in pg.execute(
            "SELECT column_name, data_type FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'foods'"
        )
    }
    assert cols["user_id"] == "uuid" and cols["processed_date"] == "date"
    assert cols["purchase_date"] == cols["expiry_date"] == "date"
    assert cols["quantity"] == "numeric" and cols["id"] == "uuid"
    assert "created_at" not in cols and "updated_at" not in cols  # 만든 시각·고친 시각 칸은 없다 (D-028)


def test_users_has_no_salt_column(pg):
    cols = {
        r["column_name"]
        for r in pg.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'users'"
        )
    }
    assert cols == {"id", "email", "password_hash"}


def test_two_indexes_for_foods(pg):
    names = {
        r["indexname"]
        for r in pg.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'foods'"
        )
    }
    assert {"foods_home_idx", "foods_records_idx"} <= names


def test_running_again_changes_nothing(pg, pg_url, pg_schema):
    upgrade(pg_url, pg_schema)
    assert TABLES <= tables(pg) and version(pg) == "0002"


def test_version_files_are_numbered_in_order():
    assert VERSIONS == ["0001_create_tables.py", "0002_block_public_api.py"]


def test_downgrade_removes_tables_and_upgrade_brings_them_back(pg, pg_url, pg_schema):
    downgrade(pg_url, pg_schema, "0001")  # 0002 만 되돌린다 (표는 그대로)
    assert TABLES <= tables(pg) and version(pg) == "0001"
    downgrade(pg_url, pg_schema, "base")
    assert not (TABLES & tables(pg)) and "alembic_version" in tables(pg)
    upgrade(pg_url, pg_schema)
    assert TABLES <= tables(pg) and version(pg) == "0002"


def test_data_survives_running_upgrade_again(pg, pg_url, pg_schema):
    pg.execute("INSERT INTO users (email, password_hash) VALUES ('keep@example.com', 'x')")
    pg.commit()
    upgrade(pg_url, pg_schema)
    assert pg.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1


def test_failed_version_file_changes_nothing(pg, pg_url, pg_schema, tmp_path):
    """0003 이 중간에 실패하면 그 파일의 일은 전부 취소되고 버전도 0002 에 머문다."""
    extra = tmp_path / "extra_versions"
    extra.mkdir()
    (extra / "0003_bad.py").write_text(
        'from alembic import op\n'
        'revision = "0003"\ndown_revision = "0002"\nbranch_labels = None\ndepends_on = None\n'
        'def upgrade():\n'
        '    op.execute("CREATE TABLE should_not_stay (id int)")\n'
        '    op.execute("SELECT 1/0")\n'
        'def downgrade():\n    pass\n',
        encoding="utf-8",
    )
    config = alembic_config(pg_url, pg_schema)
    config.set_main_option("version_locations", f"{BACKEND_DIR / 'alembic' / 'versions'} {extra}")
    config.set_main_option("path_separator", "space")
    with pytest.raises(DBAPIError) as info:
        command.upgrade(config, "head")
    assert isinstance(info.value.orig, psycopg.errors.DivisionByZero)
    assert "should_not_stay" not in tables(pg)
    assert version(pg) == "0002"


# ---- 0002: 수파베이스 REST API 역할에서 표 권한 회수 ----------------------------------------------------
@pytest.fixture
def api_roles(pg_url):
    """수파베이스에 있는 anon·authenticated 역할을 시험 동안만 만든다 (이미 있으면 건드리지 않는다)."""
    admin = psycopg.connect(pg_url, autocommit=True)
    made = []
    try:
        for role in ("anon", "authenticated"):
            if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                try:
                    admin.execute(f'CREATE ROLE "{role}" NOLOGIN')
                except psycopg.errors.InsufficientPrivilege:
                    pytest.skip("시험 DB 계정에 역할(ROLE)을 만들 권한이 없다")
                made.append(role)
        yield admin
    finally:
        for role in made:
            admin.execute(f'DROP OWNED BY "{role}"')
            admin.execute(f'DROP ROLE "{role}"')
        admin.close()


def can_read(admin, role, schema, table):
    row = admin.execute("SELECT has_table_privilege(%s, %s, 'SELECT') AS ok", (role, f'"{schema}"."{table}"'))
    return row.fetchone()["ok"]


def test_0002_revokes_api_role_access_to_every_table(pg_url, pg_schema, api_roles):
    admin = api_roles
    admin.row_factory = psycopg.rows.dict_row
    upgrade(pg_url, pg_schema, "0001")
    for role in ("anon", "authenticated"):
        admin.execute(f'GRANT USAGE ON SCHEMA "{pg_schema}" TO "{role}"')
        admin.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{pg_schema}" TO "{role}"')
    assert can_read(admin, "anon", pg_schema, "users")  # 회수 전: 열려 있다

    upgrade(pg_url, pg_schema)
    for role in ("anon", "authenticated"):
        for table in TABLES:
            assert not can_read(admin, role, pg_schema, table), (role, table)


def test_0002_does_nothing_when_the_roles_do_not_exist(pg):
    # 내 컴퓨터 PostgreSQL 처럼 anon·authenticated 가 없는 DB 에서도 올라간다 (pg 가 이미 0002 까지 올렸다)
    assert version(pg) == "0002"


def test_main_connection_helper_sees_the_schema(pg_schema, pg):
    conn = connect_test(pg_schema)
    try:
        assert TABLES <= tables(conn)
    finally:
        conn.close()
