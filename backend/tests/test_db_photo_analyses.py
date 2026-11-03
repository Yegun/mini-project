"""사진 읽기 결과(photo_analyses, PostgreSQL). 계정마다 한 줄, 30분, 남의 번호·만료·지우는 때를 본다 (DATA-MODEL 6절)."""
import uuid

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.db import photo_analyses_repo as repo
from app.db.sessions_repo import create_session

ITEMS = [
    {
        "item_no": 0,
        "name": "우유",
        "recommended_storage": "fridge",
        "storages": [
            {"storage": "room", "allowed": False, "max_days": None},
            {"storage": "fridge", "allowed": True, "max_days": 7},
            {"storage": "freezer", "allowed": True, "max_days": 30},
        ],
        "purchase_date": "2026-10-30",
        "from_rule": True,
    }
]


def age(conn, analysis_id, minutes):
    """보관한 지 minutes 분이 된 것처럼 만든다."""
    conn.execute(
        "UPDATE photo_analyses SET created_at = clock_timestamp() - make_interval(mins => %s) WHERE id = %s",
        (minutes, analysis_id),
    )


def count(conn):
    return conn.execute("SELECT count(*) AS n FROM photo_analyses").fetchone()["n"]


def test_save_and_read_back(pg, two_users):
    a, _ = two_users
    analysis_id = repo.save_analysis(pg, a["id"], ITEMS)
    got = repo.get_valid_analysis(pg, a["id"], analysis_id)
    assert got["id"] == analysis_id and got["items"] == ITEMS  # 글 목록이 그대로 돌아온다
    assert uuid.UUID(analysis_id)


def test_only_one_row_per_account_and_new_photo_replaces_the_old(pg, two_users):
    a, b = two_users
    first = repo.save_analysis(pg, a["id"], ITEMS)
    other = repo.save_analysis(pg, b["id"], ITEMS)
    second = repo.save_analysis(pg, a["id"], [])
    assert first != second and count(pg) == 2
    assert repo.get_valid_analysis(pg, a["id"], first) is None  # 이전 사진의 번호는 쓸 수 없다 (Q-29)
    assert repo.get_valid_analysis(pg, a["id"], second)["items"] == []
    assert repo.get_valid_analysis(pg, b["id"], other) is not None  # 다른 계정 것은 그대로


def test_db_does_not_allow_two_rows_for_one_account(pg, two_users):
    a, _ = two_users
    pg.execute("INSERT INTO photo_analyses (user_id, items) VALUES (%s, %s)", (a["id"], Jsonb([])))
    with pytest.raises(psycopg.errors.UniqueViolation):
        pg.execute("INSERT INTO photo_analyses (user_id, items) VALUES (%s, %s)", (a["id"], Jsonb([])))


def test_items_must_be_a_list(pg, two_users):
    a, _ = two_users
    with pytest.raises(psycopg.errors.CheckViolation):
        pg.execute("INSERT INTO photo_analyses (user_id, items) VALUES (%s, %s)", (a["id"], Jsonb({"x": 1})))


def test_another_accounts_number_is_the_same_as_a_missing_one(pg, two_users):
    a, b = two_users
    analysis_id = repo.save_analysis(pg, a["id"], ITEMS)
    assert repo.get_valid_analysis(pg, b["id"], analysis_id) is None  # 남의 번호 (D-063)
    assert repo.get_valid_analysis(pg, a["id"], str(uuid.uuid4())) is None  # 없는 번호
    assert count(pg) == 1  # 남의 번호로 물어도 그 줄은 지워지지 않는다


@pytest.mark.parametrize("bad", [None, "", "not-a-uuid", 123, "0" * 36])
def test_malformed_numbers_are_treated_as_missing(pg, two_users, bad):
    a, _ = two_users
    repo.save_analysis(pg, a["id"], ITEMS)
    assert repo.get_valid_analysis(pg, a["id"], bad) is None
    assert repo.delete_analysis(pg, a["id"], bad) is False


def test_expiry_is_judged_when_reading_and_the_expired_row_is_removed(pg, two_users):
    a, _ = two_users
    analysis_id = repo.save_analysis(pg, a["id"], ITEMS)
    age(pg, analysis_id, 29)
    assert repo.get_valid_analysis(pg, a["id"], analysis_id) is not None  # 29분은 아직 쓸 수 있다
    age(pg, analysis_id, 31)
    assert repo.get_valid_analysis(pg, a["id"], analysis_id) is None  # 30분이 지났다
    assert count(pg) == 0  # 만료된 줄을 읽으면 그 줄을 지운다 (Q-31)


def test_delete_analysis_removes_only_my_row(pg, two_users):
    a, b = two_users
    mine = repo.save_analysis(pg, a["id"], ITEMS)
    theirs = repo.save_analysis(pg, b["id"], ITEMS)
    assert repo.delete_analysis(pg, b["id"], mine) is False  # 남의 번호로는 못 지운다
    assert repo.delete_analysis(pg, a["id"], mine) is True
    assert repo.delete_analysis(pg, a["id"], mine) is False
    assert repo.get_valid_analysis(pg, b["id"], theirs) is not None


def test_delete_expired_removes_only_my_expired_row(pg, two_users):
    a, b = two_users
    mine = repo.save_analysis(pg, a["id"], ITEMS)
    theirs = repo.save_analysis(pg, b["id"], ITEMS)
    age(pg, mine, 40)
    age(pg, theirs, 40)
    assert repo.delete_expired(pg, a["id"]) == 1
    assert count(pg) == 1  # 다른 계정의 낡은 줄은 건드리지 않는다
    assert repo.delete_expired(pg, a["id"]) == 0


def test_login_removes_my_expired_row_too(pg, two_users):
    a, b = two_users
    mine = repo.save_analysis(pg, a["id"], ITEMS)
    fresh = repo.save_analysis(pg, b["id"], ITEMS)
    age(pg, mine, 31)
    create_session(pg, a["id"])  # 로그인할 때 그 계정의 만료된 줄도 같이 지운다 (Q-31)
    assert count(pg) == 1 and repo.get_valid_analysis(pg, b["id"], fresh) is not None
    # 아직 만료되지 않은 내 줄은 로그인해도 남는다
    kept = repo.save_analysis(pg, a["id"], ITEMS)
    create_session(pg, a["id"])
    assert repo.get_valid_analysis(pg, a["id"], kept) is not None


def test_deleting_the_account_deletes_the_row(pg, two_users):
    a, b = two_users
    repo.save_analysis(pg, a["id"], ITEMS)
    repo.save_analysis(pg, b["id"], ITEMS)
    pg.execute("DELETE FROM users WHERE id = %s", (a["id"],))  # 탈퇴하면 따라 지워진다 (Q-09, D-127)
    assert count(pg) == 1


def test_repo_does_not_commit_by_itself(pg, two_users):
    a, _ = two_users
    repo.save_analysis(pg, a["id"], ITEMS)
    pg.rollback()
    assert count(pg) == 0
