"""첫 가입자가 이전용 계정의 식품을 넘겨받는 일 (PostgreSQL). 한 사람에게만, 한 번만 가는지 본다."""
import psycopg
import pytest
from conftest import food_args

from app.db.foods_repo import create_food, list_active_foods, list_processed_foods, set_status
from app.db.legacy_migration import LEGACY_EMAIL, claim_legacy_foods
from app.db.users_repo import create_user


def legacy_id(pg) -> str:
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (LEGACY_EMAIL,)).fetchone()["id"])


def add_legacy_foods(pg, names=("양파", "우유", "수제청")):
    owner = legacy_id(pg)
    foods = [create_food(pg, owner, **food_args(name=n)) for n in names]
    if len(foods) > 1:
        set_status(pg, owner, foods[1]["id"], "eaten", "2026-11-02")  # 처리한 식품도 넘어간다
    pg.commit()
    return foods


def test_legacy_account_exists_after_the_versions(pg):
    assert legacy_id(pg)


def test_first_account_receives_every_legacy_food(pg):
    foods = add_legacy_foods(pg)
    first = create_user(pg, "first@example.com", "Passw0rd!")
    assert claim_legacy_foods(pg, first["id"]) == 3
    assert {f["id"] for f in list_active_foods(pg, first["id"])} == {foods[0]["id"], foods[2]["id"]}
    done = list_processed_foods(pg, first["id"])["eaten"]
    assert [(f["id"], f["processed_date"]) for f in done] == [(foods[1]["id"], "2026-11-02")]
    assert list_active_foods(pg, legacy_id(pg)) == []  # 이전용 계정에는 남지 않는다


def test_second_account_starts_empty(pg):
    add_legacy_foods(pg)
    first = create_user(pg, "first@example.com", "Passw0rd!")
    second = create_user(pg, "second@example.com", "Passw0rd!")
    assert claim_legacy_foods(pg, first["id"]) == 3
    assert claim_legacy_foods(pg, second["id"]) == 0  # 이미 넘어갔다 (D-044)
    assert list_active_foods(pg, second["id"]) == []
    assert len(list_active_foods(pg, first["id"])) == 2


def test_nothing_to_claim_when_there_were_no_legacy_foods(pg):
    user = create_user(pg, "first@example.com", "Passw0rd!")
    assert claim_legacy_foods(pg, user["id"]) == 0


def test_other_accounts_foods_are_never_touched(pg):
    add_legacy_foods(pg, names=("양파",))
    mine = create_user(pg, "mine@example.com", "Passw0rd!")
    theirs = create_user(pg, "theirs@example.com", "Passw0rd!")
    own = create_food(pg, theirs["id"], **food_args(name="남의식품"))
    pg.commit()
    claim_legacy_foods(pg, mine["id"])
    assert [f["id"] for f in list_active_foods(pg, theirs["id"])] == [own["id"]]


def test_claim_does_not_commit_by_itself(pg):
    add_legacy_foods(pg, names=("양파",))
    user = create_user(pg, "first@example.com", "Passw0rd!")
    pg.commit()
    claim_legacy_foods(pg, user["id"])
    pg.rollback()  # 가입이 취소되면 식품은 이전용 계정에 그대로 남는다
    assert len(list_active_foods(pg, legacy_id(pg))) == 1
    assert list_active_foods(pg, user["id"]) == []


def test_two_first_signups_at_once_give_the_foods_to_only_one(pg, pg_schema):
    """두 사람이 동시에 처음 가입해도 식품은 한 사람에게만 간다 (먼저 넘긴 쪽이 행을 잠근다)."""
    from app.db.connection import connect_test

    add_legacy_foods(pg)
    a = create_user(pg, "a@example.com", "Passw0rd!")
    b = create_user(pg, "b@example.com", "Passw0rd!")
    pg.commit()
    other = connect_test(pg_schema)
    try:
        assert claim_legacy_foods(pg, a["id"]) == 3  # a 의 가입 묶음이 아직 commit 전
        other.execute("SET lock_timeout = '300ms'")
        with pytest.raises(psycopg.errors.LockNotAvailable):  # b 는 a 가 끝날 때까지 기다린다
            claim_legacy_foods(other, b["id"])
        other.rollback()
        pg.commit()  # a 가 끝나면
        assert claim_legacy_foods(other, b["id"]) == 0  # b 는 이미 넘어간 식품을 찾지 못한다
        other.commit()
    finally:
        other.close()
    assert len(list_active_foods(pg, a["id"])) == 2 and list_active_foods(pg, b["id"]) == []


def test_nobody_can_log_in_as_the_legacy_account(pg):
    from app.db.users_repo import authenticate

    assert authenticate(pg, LEGACY_EMAIL, "!") is None
    assert authenticate(pg, LEGACY_EMAIL, "Passw0rd!") is None
