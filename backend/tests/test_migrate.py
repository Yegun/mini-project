"""알렘빅 버전 파일 6개 (PostgreSQL 임시 schema). 번호 순서, 올리기·되돌리기, 한 단계씩의 결과, 실패하면 그 파일만 취소."""
import sqlite3
import uuid
from datetime import date

import psycopg
import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.db.connection import BACKEND_DIR, connect_test
from app.db.legacy_migration import LEGACY_EMAIL
from app.db.migrate import alembic_config, downgrade, upgrade
from app.db.users_repo import authenticate

TABLES = {"users", "sessions", "foods", "rules", "rule_aliases", "rule_storage"}
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"
HEAD = "0006"


def tables(conn):
    rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")
    return {r["table_name"] for r in rows}


def version(conn):
    row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    conn.rollback()
    return row["version_num"] if row else None


def count(conn, sql, *params):
    return conn.execute(sql, params).fetchone()["n"]


@pytest.fixture
def db(pg_url, pg_schema):
    """빈 임시 schema. 시험이 원하는 버전까지 올린다. conn() 으로 같은 schema 에 연결한다."""

    class Db:
        url, schema = pg_url, pg_schema

        def up(self, revision="head"):
            upgrade(pg_url, pg_schema, revision)

        def down(self, revision):
            downgrade(pg_url, pg_schema, revision)

        def conn(self):
            return connect_test(pg_schema)

    return Db()


def make_legacy_file(path, rows=None):
    """v0.2.0 모양의 옛 SQLite 식품 파일."""
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE foods (id TEXT, name TEXT, storage TEXT, quantity REAL, unit TEXT,"
        " purchase_date TEXT, expiry_date TEXT, source TEXT, status TEXT)"
    )
    db.executemany(
        "INSERT INTO foods VALUES (?,?,?,?,?,?,?,?,?)",
        rows
        or [
            (OLD[0], "양파", "room", 2, "개", "2026-10-01", "2026-10-31", "rule", "none"),
            (OLD[1], "우유", "fridge", 1.5, "L", "2026-10-20", "2026-10-27", "rule", "eaten"),
            (OLD[2], "수제청", "room", 1, "병", "2026-10-02", "2026-12-02", "manual", "discarded"),
        ],
    )
    db.commit()
    db.close()


OLD = [str(uuid.uuid4()) for _ in range(3)]


# ---- 번호와 순서 ---------------------------------------------------------------------------------
def test_version_files_are_numbered_in_order():
    names = sorted(p.name for p in VERSIONS_DIR.glob("0*.py"))
    assert names == [
        "0001_create_tables.py", "0002_import_legacy_foods.py", "0003_create_legacy_owner_account.py",
        "0004_assign_ownerless_foods.py", "0005_foods_owner_required.py", "0006_block_public_api.py",
    ]


def test_each_version_points_to_the_one_before():
    for number in range(1, 7):
        text = next(VERSIONS_DIR.glob(f"000{number}_*.py")).read_text(encoding="utf-8")
        assert f'revision = "000{number}"' in text
        assert ("down_revision = None" if number == 1 else f'down_revision = "000{number - 1}"') in text


def test_legacy_email_is_the_same_in_code_and_versions():
    for name in ("0003_create_legacy_owner_account.py", "0004_assign_ownerless_foods.py"):
        assert f'LEGACY_EMAIL = "{LEGACY_EMAIL}"' in (VERSIONS_DIR / name).read_text(encoding="utf-8")


# ---- 0001 새 DB 구조 --------------------------------------------------------------------------------
def test_0001_creates_six_tables_and_owner_column_may_be_empty(db):
    db.up("0001")
    conn = db.conn()
    assert TABLES <= tables(conn) and "legacy_migration" not in tables(conn)
    cols = {
        r["column_name"]: (r["data_type"], r["is_nullable"])
        for r in conn.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = 'foods'"
        )
    }
    assert cols["user_id"] == ("uuid", "YES")  # 처음에는 비울 수 있다
    assert cols["processed_date"][0] == "date" and cols["quantity"][0] == "numeric"
    assert "created_at" not in cols and "updated_at" not in cols  # 만든 시각·고친 시각 칸은 없다 (D-028)
    assert version(conn) == "0001"
    conn.close()


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


# ---- 0002 옛 식품 가져오기 (주인 없이) ---------------------------------------------------------------------
def test_0002_imports_legacy_foods_without_owner_and_keeps_ids(db, tmp_path, monkeypatch):
    legacy = tmp_path / "old.db"
    make_legacy_file(legacy)
    monkeypatch.setenv("FRIDGE_DB_PATH", str(legacy))
    monkeypatch.setattr("app.database.get_today", lambda: date(2026, 11, 2))
    db.up("0002")
    conn = db.conn()
    rows = {str(r["id"]): r for r in conn.execute("SELECT * FROM foods")}
    assert set(rows) == set(OLD)  # 옛 번호 그대로 (Q-17)
    assert all(r["user_id"] is None for r in rows.values())  # 아직 주인 없이
    assert (rows[OLD[0]]["status"], rows[OLD[0]]["processed_date"]) == ("none", None)
    assert rows[OLD[1]]["processed_date"] == date(2026, 11, 2)  # 처리한 식품은 옮긴 날 (D-045)
    assert rows[OLD[2]]["processed_date"] == date(2026, 11, 2) and rows[OLD[2]]["status"] == "discarded"
    assert float(rows[OLD[1]]["quantity"]) == 1.5 and rows[OLD[1]]["expiry_date"] == date(2026, 10, 27)
    assert version(conn) == "0002"
    conn.close()


def test_0002_leaves_the_sqlite_file_untouched(db, tmp_path, monkeypatch):
    legacy = tmp_path / "old.db"
    make_legacy_file(legacy)
    before = legacy.read_bytes()
    monkeypatch.setenv("FRIDGE_DB_PATH", str(legacy))
    db.up("0002")
    assert legacy.read_bytes() == before  # 백업으로 남긴다 (D-098)


def test_0002_does_nothing_without_a_file_or_foods(db, tmp_path):
    db.up("0002")  # 없는 파일 (conftest 가 없는 경로로 돌려 둔다)
    conn = db.conn()
    assert count(conn, "SELECT count(*) AS n FROM foods") == 0 and version(conn) == "0002"
    conn.close()


def test_0002_skips_a_file_without_foods_table(db, tmp_path, monkeypatch):
    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()
    monkeypatch.setenv("FRIDGE_DB_PATH", str(empty))
    db.up("0002")
    conn = db.conn()
    assert count(conn, "SELECT count(*) AS n FROM foods") == 0
    conn.close()


def test_0002_failure_imports_nothing(db, tmp_path, monkeypatch):
    legacy = tmp_path / "old.db"
    make_legacy_file(legacy)
    sql = sqlite3.connect(legacy)
    sql.execute("UPDATE foods SET quantity = 0 WHERE id = ?", (OLD[2],))  # 마지막 줄이 DB 규칙에 걸린다
    sql.commit()
    sql.close()
    monkeypatch.setenv("FRIDGE_DB_PATH", str(legacy))
    db.up("0001")
    with pytest.raises(DBAPIError):
        db.up("0002")
    conn = db.conn()
    assert count(conn, "SELECT count(*) AS n FROM foods") == 0  # 일부만 가져오지 않는다
    assert version(conn) == "0001"
    conn.close()


def test_0002_downgrade_removes_only_ownerless_foods(db, tmp_path, monkeypatch):
    legacy = tmp_path / "old.db"
    make_legacy_file(legacy)
    monkeypatch.setenv("FRIDGE_DB_PATH", str(legacy))
    db.up("0002")
    db.down("0001")
    conn = db.conn()
    assert count(conn, "SELECT count(*) AS n FROM foods") == 0 and version(conn) == "0001"
    conn.close()


# ---- 0003 이전용 계정 ------------------------------------------------------------------------------
def test_0003_creates_an_account_nobody_can_log_in_to(db):
    db.up("0003")
    conn = db.conn()
    row = conn.execute("SELECT email, password_hash FROM users").fetchone()
    assert row["email"] == LEGACY_EMAIL == "legacy@fridge.invalid"
    assert row["password_hash"] == "!"  # 해시가 아니라서 어떤 비밀번호도 맞지 않는다
    for password in ("!", "", "legacy", "Passw0rd!", "!!"):
        assert authenticate(conn, LEGACY_EMAIL, password) is None
    conn.close()


def test_0003_downgrade_removes_the_account(db):
    db.up("0003")
    db.down("0002")
    conn = db.conn()
    assert count(conn, "SELECT count(*) AS n FROM users") == 0
    conn.close()


# ---- 0004 주인 없는 식품을 이전용 계정에 넘기기 -------------------------------------------------------------
def test_0004_gives_every_ownerless_food_to_the_legacy_account(db, tmp_path, monkeypatch):
    legacy = tmp_path / "old.db"
    make_legacy_file(legacy)
    monkeypatch.setenv("FRIDGE_DB_PATH", str(legacy))
    db.up("0004")
    conn = db.conn()
    assert count(conn, "SELECT count(*) AS n FROM foods WHERE user_id IS NULL") == 0
    owners = {str(r["user_id"]) for r in conn.execute("SELECT user_id FROM foods")}
    legacy_id = str(conn.execute("SELECT id FROM users WHERE email = %s", (LEGACY_EMAIL,)).fetchone()["id"])
    assert owners == {legacy_id} and count(conn, "SELECT count(*) AS n FROM foods") == 3
    conn.close()


def test_0004_downgrade_makes_only_the_legacy_foods_ownerless_again(db, tmp_path, monkeypatch):
    legacy = tmp_path / "old.db"
    make_legacy_file(legacy)
    monkeypatch.setenv("FRIDGE_DB_PATH", str(legacy))
    db.up("0004")
    conn = db.conn()
    real = conn.execute("INSERT INTO users (email, password_hash) VALUES ('kim@example.com', 'x') RETURNING id").fetchone()["id"]
    conn.execute(
        "INSERT INTO foods (user_id, name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " VALUES (%s, '내식품', 'room', 1, '개', '2026-10-30', '2026-11-30', 'manual')", (real,)
    )
    conn.commit()
    db.down("0003")
    assert count(conn, "SELECT count(*) AS n FROM foods WHERE user_id IS NULL") == 3  # 이전용 계정 것만
    assert count(conn, "SELECT count(*) AS n FROM foods WHERE user_id = %s", real) == 1  # 진짜 사용자 것은 그대로
    conn.close()


# ---- 0005 주인 칸을 비울 수 없게 --------------------------------------------------------------------------
def test_0005_requires_an_owner_that_exists_and_cascades(db):
    db.up()
    conn = db.conn()
    insert = (
        "INSERT INTO foods (user_id, name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " VALUES (%s, '식품', 'room', 1, '개', '2026-10-30', '2026-11-30', 'manual')"
    )
    with pytest.raises(psycopg.errors.NotNullViolation):
        conn.execute(insert, (None,))
    conn.rollback()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(insert, (str(uuid.uuid4()),))
    conn.rollback()
    uid = conn.execute("INSERT INTO users (email, password_hash) VALUES ('kim@example.com', 'x') RETURNING id").fetchone()["id"]
    conn.execute(insert, (uid,))
    conn.execute("DELETE FROM users WHERE id = %s", (uid,))  # 계정을 지우면 식품도 지워진다 (Q-09)
    assert count(conn, "SELECT count(*) AS n FROM foods") == 0
    conn.close()


def test_0005_fails_and_changes_nothing_if_an_ownerless_food_remains(db):
    db.up("0004")
    conn = db.conn()
    conn.execute(  # 0004 뒤에 누군가 주인 없는 식품을 만들었다
        "INSERT INTO foods (name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " VALUES ('주인없음', 'room', 1, '개', '2026-10-30', '2026-11-30', 'manual')"
    )
    conn.commit()
    with pytest.raises(DBAPIError) as info:
        db.up("0005")
    assert isinstance(info.value.orig, psycopg.errors.NotNullViolation)
    assert version(conn) == "0004"
    nullable = conn.execute(
        "SELECT is_nullable FROM information_schema.columns"
        " WHERE table_schema = current_schema() AND table_name = 'foods' AND column_name = 'user_id'"
    ).fetchone()["is_nullable"]
    assert nullable == "YES"  # 아무것도 바뀌지 않았다
    conn.close()


def test_0005_downgrade_allows_an_empty_owner_again(db):
    db.up("0005")
    db.down("0004")
    conn = db.conn()
    conn.execute(
        "INSERT INTO foods (name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " VALUES ('주인없음', 'room', 1, '개', '2026-10-30', '2026-11-30', 'manual')"
    )
    conn.close()


# ---- 0006 수파베이스 REST API 역할에서 표 권한 회수 ---------------------------------------------------------
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


def test_0006_revokes_api_role_access_to_every_table(db, api_roles):
    admin = api_roles
    admin.row_factory = psycopg.rows.dict_row
    db.up("0005")
    for role in ("anon", "authenticated"):
        admin.execute(f'GRANT USAGE ON SCHEMA "{db.schema}" TO "{role}"')
        admin.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA "{db.schema}" TO "{role}"')
    assert can_read(admin, "anon", db.schema, "users")  # 회수 전: 열려 있다

    db.up()
    for role in ("anon", "authenticated"):
        for table in TABLES:
            assert not can_read(admin, role, db.schema, table), (role, table)


def test_0006_does_nothing_when_the_roles_do_not_exist(pg):
    # 내 컴퓨터 PostgreSQL 처럼 anon·authenticated 가 없는 DB 에서도 올라간다 (pg 가 이미 0006 까지 올렸다)
    assert version(pg) == HEAD


# ---- 전체 ----------------------------------------------------------------------------------------
def test_upgrade_to_head_builds_everything(pg):
    assert TABLES <= tables(pg)
    assert version(pg) == HEAD
    assert count(pg, "SELECT count(*) AS n FROM users WHERE email = %s", LEGACY_EMAIL) == 1  # 이전용 계정


def test_running_again_changes_nothing(pg, pg_url, pg_schema):
    upgrade(pg_url, pg_schema)
    assert TABLES <= tables(pg) and version(pg) == HEAD
    assert count(pg, "SELECT count(*) AS n FROM users") == 1  # 이전용 계정이 두 번 만들어지지 않는다


def test_downgrade_all_the_way_and_up_again(pg, pg_url, pg_schema):
    downgrade(pg_url, pg_schema, "base")
    assert not (TABLES & tables(pg)) and "alembic_version" in tables(pg)
    upgrade(pg_url, pg_schema)
    assert TABLES <= tables(pg) and version(pg) == HEAD


def test_data_survives_running_upgrade_again(pg, pg_url, pg_schema):
    pg.execute("INSERT INTO users (email, password_hash) VALUES ('keep@example.com', 'x')")
    pg.commit()
    upgrade(pg_url, pg_schema)
    assert count(pg, "SELECT count(*) AS n FROM users WHERE email = 'keep@example.com'") == 1


def test_failed_version_file_changes_nothing(pg, pg_url, pg_schema, tmp_path):
    """0007 이 중간에 실패하면 그 파일의 일은 전부 취소되고 버전도 0006 에 머문다."""
    extra = tmp_path / "extra_versions"
    extra.mkdir()
    (extra / "0007_bad.py").write_text(
        'from alembic import op\n'
        'revision = "0007"\ndown_revision = "0006"\nbranch_labels = None\ndepends_on = None\n'
        'def upgrade():\n'
        '    op.execute("CREATE TABLE should_not_stay (id int)")\n'
        '    op.execute("SELECT 1/0")\n'
        'def downgrade():\n    pass\n',
        encoding="utf-8",
    )
    config = alembic_config(pg_url, pg_schema)
    config.set_main_option("version_locations", f"{VERSIONS_DIR} {extra}")
    config.set_main_option("path_separator", "space")
    with pytest.raises(DBAPIError) as info:
        command.upgrade(config, "head")
    assert isinstance(info.value.orig, psycopg.errors.DivisionByZero)
    assert "should_not_stay" not in tables(pg)
    assert version(pg) == HEAD
