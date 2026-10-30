from datetime import date
from decimal import Decimal

import pytest

from app import repo_foods


def make(conn, **overrides):
    values = {
        "name": "두부",
        "storage": "fridge",
        "quantity": Decimal("1"),
        "unit": "모",
        "purchase_date": date(2026, 10, 30),
        "expiry_date": date(2026, 11, 6),
        "source": "rule",
    }
    values.update(overrides)
    return repo_foods.create_food(conn, **values)


# 만들기: 번호는 시스템이 UUID 로 만들고, 처리 상태는 "none" 으로 시작한다 (D-033, DATA-MODEL 5절)
def test_create_food_fills_id_and_status(conn):
    food = make(conn)
    assert len(food["id"]) == 36
    assert food["status"] == "none"
    assert food["name"] == "두부"
    assert food["quantity"] == 1.0
    assert food["purchase_date"] == date(2026, 10, 30)
    assert food["expiry_date"] == date(2026, 11, 6)
    assert food["source"] == "rule"


def test_same_name_can_be_created_many_times(conn):
    first = make(conn)
    second = make(conn)
    assert first["id"] != second["id"]
    assert len(repo_foods.list_active_foods(conn)) == 2


def test_dates_are_stored_as_yyyy_mm_dd_text(conn):
    food = make(conn)
    row = conn.execute(
        "SELECT purchase_date, expiry_date FROM foods WHERE id = ?", (food["id"],)
    ).fetchone()
    assert row == ("2026-10-30", "2026-11-06")


# 읽기
def test_get_food_returns_the_food_or_none(conn):
    food = make(conn)
    assert repo_foods.get_food(conn, food["id"]) == food
    assert repo_foods.get_food(conn, "없는-번호") is None


def test_list_active_foods_only_shows_status_none(conn):
    keep = make(conn, name="당근")
    eaten = make(conn, name="우유")
    thrown = make(conn, name="달걀")
    repo_foods.set_status(conn, eaten["id"], "eaten")
    repo_foods.set_status(conn, thrown["id"], "discarded")
    assert repo_foods.list_active_foods(conn) == [keep]


def test_list_active_foods_empty(conn):
    assert repo_foods.list_active_foods(conn) == []


# 고치기: 정해진 칸만 고칠 수 있다. 번호와 처리 상태는 여기서 못 바꾼다
def test_update_food_changes_only_given_fields(conn):
    food = make(conn)
    updated = repo_foods.update_food(
        conn, food["id"], name="순두부", quantity=Decimal("2.5"), expiry_date=date(2026, 11, 8)
    )
    assert updated["name"] == "순두부"
    assert updated["quantity"] == 2.5
    assert updated["expiry_date"] == date(2026, 11, 8)
    assert updated["unit"] == "모"
    assert updated["storage"] == "fridge"
    assert repo_foods.get_food(conn, food["id"]) == updated


def test_update_food_with_no_fields_changes_nothing(conn):
    food = make(conn)
    assert repo_foods.update_food(conn, food["id"]) == food


def test_update_food_missing_returns_none(conn):
    assert repo_foods.update_food(conn, "없는-번호", name="가") is None


def test_update_food_rejects_fields_it_must_not_change(conn):
    food = make(conn)
    with pytest.raises(ValueError):
        repo_foods.update_food(conn, food["id"], id="다른-번호")
    with pytest.raises(ValueError):
        repo_foods.update_food(conn, food["id"], status="eaten")


# 처리: 다 먹음 / 버림만 가능하고 되돌리기는 없다 (D-013)
def test_set_status_keeps_the_row(conn):
    food = make(conn)
    assert repo_foods.set_status(conn, food["id"], "eaten") is True
    assert repo_foods.get_food(conn, food["id"])["status"] == "eaten"


def test_set_status_missing_returns_false(conn):
    assert repo_foods.set_status(conn, "없는-번호", "eaten") is False


def test_set_status_cannot_go_back_to_none(conn):
    food = make(conn)
    with pytest.raises(ValueError):
        repo_foods.set_status(conn, food["id"], "none")
    with pytest.raises(ValueError):
        repo_foods.set_status(conn, food["id"], "아무거나")


# 삭제: 행을 완전히 지운다 (D-013)
def test_delete_food_removes_the_row(conn):
    food = make(conn)
    assert repo_foods.delete_food(conn, food["id"]) is True
    assert repo_foods.get_food(conn, food["id"]) is None
    assert conn.execute("SELECT COUNT(*) FROM foods").fetchone() == (0,)


def test_delete_food_missing_returns_false(conn):
    assert repo_foods.delete_food(conn, "없는-번호") is False


# 저장 확정(commit)은 부른 쪽이 한다. 실패하면 되돌려서 아무것도 안 바뀐다 (OQ-04)
def test_repo_does_not_commit_by_itself(conn):
    make(conn)
    conn.rollback()
    assert repo_foods.list_active_foods(conn) == []
