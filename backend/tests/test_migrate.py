"""표 만들기 (PostgreSQL). 7개 표, 여러 번 실행해도 안전, 중간에 실패하면 아무것도 안 바뀜을 본다."""
import psycopg
import pytest

from app.db import migrate
from app.db.migrate import MIGRATIONS_DIR, apply_migrations

TABLES = {"users", "sessions", "foods", "rules", "rule_aliases", "rule_storage", "legacy_migration"}


def tables(conn):
    rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")
    return {r["table_name"] for r in rows}


def test_creates_the_seven_tables(pg):
    assert TABLES <= tables(pg)


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


def test_running_again_does_nothing(pg):
    assert apply_migrations(pg) == []
    assert TABLES <= tables(pg)
    versions = [r["version"] for r in pg.execute("SELECT version FROM schema_migrations")]
    assert versions == sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))


def test_two_indexes_for_foods(pg):
    names = {
        r["indexname"]
        for r in pg.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'foods'"
        )
    }
    assert {"foods_home_idx", "foods_records_idx"} <= names


def test_failed_file_changes_nothing(pg, tmp_path, monkeypatch):
    (tmp_path / "0002_bad.sql").write_text(
        "CREATE TABLE should_not_stay (id int);\nSELECT 1/0;", encoding="utf-8"
    )
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", tmp_path)
    with pytest.raises(psycopg.errors.DivisionByZero):
        apply_migrations(pg)
    assert "should_not_stay" not in tables(pg)
    assert pg.execute("SELECT count(*) AS n FROM schema_migrations WHERE version = '0002_bad.sql'").fetchone()["n"] == 0
