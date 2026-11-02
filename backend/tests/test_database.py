"""DB 연결·한 요청 = 한 묶음·한국 시간 오늘 (API-SPEC 0절)."""
from datetime import datetime, timezone

import psycopg
import pytest

import app.database as database
from app.db.users_repo import create_user
from app.errors import ApiError
from app.validation import ValidationError


class FakeNow:
    """datetime.now(tz) 를 고정한 시각으로 바꿔 끼우는 시험용 가짜."""

    def __init__(self, utc: datetime):
        self.utc = utc

    def now(self, tz=None):
        return self.utc.astimezone(tz)


def set_utc_now(monkeypatch, *args):
    monkeypatch.setattr(database, "datetime", FakeNow(datetime(*args, tzinfo=timezone.utc)))


def test_today_is_korea_time_and_changes_at_korean_midnight(monkeypatch):
    set_utc_now(monkeypatch, 2026, 10, 30, 14, 59)  # 한국 23:59
    assert database.get_today().isoformat() == "2026-10-30"
    set_utc_now(monkeypatch, 2026, 10, 30, 15, 0)  # 한국 0:00
    assert database.get_today().isoformat() == "2026-10-31"


def test_today_crosses_year_end(monkeypatch):
    set_utc_now(monkeypatch, 2026, 12, 31, 15, 30)
    assert database.get_today().isoformat() == "2027-01-01"


def test_transaction_commits_on_success(pg):
    with database.transaction(pg):
        create_user(pg, "kim@example.com", "Passw0rd!")
    pg.rollback()  # commit 됐다면 rollback 해도 남아 있다
    assert pg.execute("SELECT count(*) AS n FROM users WHERE email <> 'legacy@fridge.invalid'").fetchone()["n"] == 1


def test_transaction_rolls_back_everything_on_api_error(pg):
    with pytest.raises(ApiError) as info:
        with database.transaction(pg):
            create_user(pg, "kim@example.com", "Passw0rd!")
            raise ApiError("expiry_required", "expiry_date")
    assert info.value.reason == "expiry_required"  # 입력 오류는 그대로 낸다
    assert pg.execute("SELECT count(*) AS n FROM users WHERE email <> 'legacy@fridge.invalid'").fetchone()["n"] == 0


def test_transaction_rolls_back_on_validation_error(pg):
    with pytest.raises(ValidationError):
        with database.transaction(pg):
            create_user(pg, "kim@example.com", "Passw0rd!")
            raise ValidationError("quantity", "invalid_quantity")
    assert pg.execute("SELECT count(*) AS n FROM users WHERE email <> 'legacy@fridge.invalid'").fetchone()["n"] == 0


def test_db_trouble_becomes_server_error_and_changes_nothing(pg):
    create_user(pg, "first@example.com", "Passw0rd!")
    pg.commit()
    with pytest.raises(ApiError) as info:
        with database.transaction(pg):
            create_user(pg, "second@example.com", "Passw0rd!")
            pg.execute("INSERT INTO foods (user_id, name) VALUES (gen_random_uuid(), 'x')")  # 빠진 칸 → DB 오류
    assert info.value.reason == "server_error" and info.value.status_code == 500
    assert pg.execute("SELECT count(*) AS n FROM users WHERE email <> 'legacy@fridge.invalid'").fetchone()["n"] == 1


def test_cannot_connect_is_server_error(monkeypatch):
    def refuse():
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(database, "connect_app", refuse)
    with pytest.raises(ApiError) as info:
        next(database.get_conn())
    assert info.value.reason == "server_error"


def test_missing_setting_is_server_error(monkeypatch):
    def missing():
        raise database.DatabaseConfigError("no DATABASE_URL")

    monkeypatch.setattr(database, "connect_app", missing)
    with pytest.raises(ApiError) as info:
        next(database.get_conn())
    assert info.value.reason == "server_error"


def test_get_conn_closes_the_connection(monkeypatch):
    class Conn:
        closed = False

        def close(self):
            self.closed = True

    conn = Conn()
    monkeypatch.setattr(database, "connect_app", lambda: conn)
    generator = database.get_conn()
    assert next(generator) is conn
    with pytest.raises(StopIteration):
        next(generator)
    assert conn.closed
