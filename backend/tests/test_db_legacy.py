"""기존 식품(v0.2.0 SQLite) 옮기기 (PostgreSQL). 첫 계정만, 한 번만, 실패하면 그 묶음만 취소되는지 본다."""
import sqlite3
import uuid

import psycopg
import pytest

from app.db.foods_repo import get_food, list_active_foods, list_processed_foods
from app.db.legacy_migration import migrate_legacy_foods, needs_migration, register_first_user
from app.db.users_repo import create_user

TODAY = "2026-11-02"
OLD_ID_1, OLD_ID_2, OLD_ID_3 = (str(uuid.uuid4()) for _ in range(3))


@pytest.fixture
def legacy(tmp_path):
    """v0.2.0 모양의 옛 SQLite 파일. 식품 3건 (처리 전 1, 다 먹음 1, 버림 1)."""
    path = tmp_path / "fridge.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE foods (id TEXT, name TEXT, storage TEXT, quantity REAL, unit TEXT,"
        " purchase_date TEXT, expiry_date TEXT, source TEXT, status TEXT)"
    )
    rows = [
        (OLD_ID_1, "양파", "room", 2, "개", "2026-10-01", "2026-10-31", "rule", "none"),
        (OLD_ID_2, "우유", "fridge", 1.5, "L", "2026-10-20", "2026-10-27", "rule", "eaten"),
        (OLD_ID_3, "수제청", "room", 1, "병", "2026-10-02", "2026-12-02", "manual", "discarded"),
    ]
    db.executemany("INSERT INTO foods VALUES (?,?,?,?,?,?,?,?,?)", rows)
    db.commit()
    db.close()
    return path


def first_user(pg):
    user = create_user(pg, "first@example.com", "Passw0rd!")
    assert register_first_user(pg, user["id"]) is True
    return user


def test_first_account_is_decided_only_once(pg):
    first = create_user(pg, "first@example.com", "Passw0rd!")
    second = create_user(pg, "second@example.com", "Passw0rd!")
    assert register_first_user(pg, first["id"]) is True
    assert register_first_user(pg, second["id"]) is False  # 이후 가입하는 계정은 빈 상태 (D-044)
    row = pg.execute("SELECT user_id, migrated FROM legacy_migration").fetchall()
    assert len(row) == 1 and str(row[0]["user_id"]) == first["id"] and row[0]["migrated"] is False


def test_migrates_foods_to_first_account_keeping_ids(pg, legacy):
    user = first_user(pg)
    assert needs_migration(pg, user["id"]) is True
    assert migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=legacy) is True

    active = list_active_foods(pg, user["id"])
    assert [f["id"] for f in active] == [OLD_ID_1]  # 기존 번호 그대로 (Q-17)
    assert active[0]["quantity"] == 2 and active[0]["source"] == "rule"
    processed = list_processed_foods(pg, user["id"])
    # 이미 처리한 식품의 처리한 날짜는 옮기는 날이다 (D-045)
    assert [(f["id"], f["processed_date"]) for f in processed["eaten"]] == [(OLD_ID_2, TODAY)]
    assert [(f["id"], f["processed_date"]) for f in processed["discarded"]] == [(OLD_ID_3, TODAY)]
    assert processed["eaten"][0]["quantity"] == 1.5
    assert get_food(pg, user["id"], OLD_ID_1)["status"] == "none"
    assert needs_migration(pg, user["id"]) is False


def test_migrates_only_once(pg, legacy):
    user = first_user(pg)
    assert migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=legacy) is True
    assert migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=legacy) is False  # 두 번 옮기지 않는다
    assert pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"] == 3


def test_other_accounts_never_get_legacy_foods(pg, legacy):
    first_user(pg)
    other = create_user(pg, "second@example.com", "Passw0rd!")
    assert register_first_user(pg, other["id"]) is False
    assert needs_migration(pg, other["id"]) is False
    assert migrate_legacy_foods(pg, other["id"], TODAY, legacy_path=legacy) is False
    assert list_active_foods(pg, other["id"]) == []


def test_failure_cancels_only_the_migration(pg, legacy):
    """옮기다 실패하면 복사는 전부 취소되고 가입(계정·옮김 기록)은 그대로다 (D-097)."""
    db = sqlite3.connect(legacy)
    db.execute("UPDATE foods SET quantity = 0 WHERE id = ?", (OLD_ID_3,))  # 마지막 줄이 DB 규칙에 걸린다
    db.commit()
    db.close()
    user = first_user(pg)
    pg.commit()

    with pytest.raises(psycopg.errors.CheckViolation):
        migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=legacy)

    assert pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"] == 0  # 일부만 옮겨지지 않는다
    assert pg.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1  # 계정은 그대로
    assert needs_migration(pg, user["id"]) is True  # 다음 로그인 때 다시 시도한다
    pg.commit()  # 같은 묶음(가입)은 계속 commit 할 수 있다

    db = sqlite3.connect(legacy)  # 원인을 고친 뒤 다시 시도하면 성공한다
    db.execute("UPDATE foods SET quantity = 1 WHERE id = ?", (OLD_ID_3,))
    db.commit()
    db.close()
    assert migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=legacy) is True
    assert pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"] == 3


def test_missing_sqlite_file_finishes_immediately(pg, tmp_path):
    user = first_user(pg)
    assert migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=tmp_path / "none.db") is True
    assert needs_migration(pg, user["id"]) is False
    assert list_active_foods(pg, user["id"]) == []


def test_sqlite_file_is_left_untouched(pg, legacy):
    before = legacy.read_bytes()
    user = first_user(pg)
    migrate_legacy_foods(pg, user["id"], TODAY, legacy_path=legacy)
    assert legacy.read_bytes() == before  # 백업으로 남긴다 (D-098)


def test_record_survives_account_deletion(pg):
    user = first_user(pg)
    pg.execute("UPDATE legacy_migration SET migrated = true")
    pg.execute("DELETE FROM users WHERE id = %s", (user["id"],))
    row = pg.execute("SELECT user_id, migrated FROM legacy_migration").fetchone()
    assert row["user_id"] is None and row["migrated"] is True  # 줄은 남아 "옮김이 끝났다"를 유지 (Q-09)


def test_only_one_row_allowed(pg):
    a = create_user(pg, "a@example.com", "Passw0rd!")
    with pytest.raises(psycopg.errors.CheckViolation):
        pg.execute("INSERT INTO legacy_migration (id, user_id) VALUES (2, %s)", (a["id"],))
