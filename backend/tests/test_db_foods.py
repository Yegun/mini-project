import sqlite3

import pytest

from app.db.connection import connect_foods
from app.db.foods_repo import (
    create_food,
    delete_food,
    get_food,
    list_active_foods,
    set_status,
    update_food,
)
from app.db.schema import create_foods_schema


@pytest.fixture
def conn(tmp_path):
    c = connect_foods(tmp_path / "fridge.db")
    create_foods_schema(c)
    yield c
    c.close()


def make(conn, **over):
    data = dict(
        name="양파", storage="room", quantity=2, unit="개",
        purchase_date="2026-10-30", expiry_date="2026-11-29", source="rule",
    )
    data.update(over)
    return create_food(conn, **data)


def test_create_then_read_same_values(conn):
    food = make(conn, quantity=0.25)
    assert len(food["id"]) == 36
    assert food["status"] == "none"
    assert food["quantity"] == 0.25
    assert get_food(conn, food["id"]) == food


def test_same_name_twice_allowed(conn):
    a, b = make(conn), make(conn)
    assert a["id"] != b["id"]
    assert len(list_active_foods(conn)) == 2


@pytest.mark.parametrize(
    "bad",
    [
        {"name": ""},
        {"name": "   "},
        {"unit": ""},
        {"quantity": 0},
        {"quantity": -1},
        {"storage": "shelf"},
        {"source": "photo"},
        {"purchase_date": "2026-13-40"},
        {"purchase_date": "10/30"},
        {"expiry_date": "내일"},
        {"purchase_date": "2026-11-30", "expiry_date": "2026-11-29"},  # 구매일 > 기한 (D-003)
    ],
)
def test_bad_values_rejected_and_nothing_saved(conn, bad):
    with pytest.raises(sqlite3.IntegrityError):
        make(conn, **bad)
    assert list_active_foods(conn) == []


def test_purchase_equals_expiry_ok(conn):
    make(conn, purchase_date="2026-10-30", expiry_date="2026-10-30")


def test_list_order_and_only_active(conn):
    late = make(conn, name="가", expiry_date="2026-12-01")
    same_b = make(conn, name="나", expiry_date="2026-11-05", purchase_date="2026-10-30")
    same_a = make(conn, name="다", expiry_date="2026-11-05", purchase_date="2026-10-30")
    older = make(conn, name="라", expiry_date="2026-11-05", purchase_date="2026-10-20")
    eaten = make(conn, name="마", expiry_date="2026-10-31")
    set_status(conn, eaten["id"], "eaten")
    ids = [f["id"] for f in list_active_foods(conn)]
    # 기한 빠른 순 → 구매일 이른 순 → 이름순
    assert ids == [older["id"], same_b["id"], same_a["id"], late["id"]]


def test_update_changes_only_given_fields(conn):
    food = make(conn)
    updated = update_food(conn, food["id"], name="대파", quantity=3)
    assert updated["name"] == "대파" and updated["quantity"] == 3
    assert updated["expiry_date"] == food["expiry_date"]


def test_update_rejects_bad_value_and_keeps_old(conn):
    food = make(conn)
    with pytest.raises(sqlite3.IntegrityError):
        update_food(conn, food["id"], purchase_date="2026-12-31")  # 기한보다 뒤
    assert get_food(conn, food["id"]) == food


def test_update_cannot_touch_id_or_status(conn):
    food = make(conn)
    with pytest.raises(ValueError):
        update_food(conn, food["id"], status="eaten")
    with pytest.raises(ValueError):
        update_food(conn, food["id"], id="x")


def test_update_missing_returns_none(conn):
    assert update_food(conn, "no-such-id", name="a") is None


def test_set_status_keeps_row_and_hides_from_list(conn):
    food = make(conn)
    done = set_status(conn, food["id"], "discarded")
    assert done["status"] == "discarded"
    assert list_active_foods(conn) == []
    assert get_food(conn, food["id"]) is None
    assert get_food(conn, food["id"], include_processed=True)["status"] == "discarded"


def test_processed_food_cannot_be_processed_again_updated_or_deleted(conn):
    food = make(conn)
    set_status(conn, food["id"], "eaten")
    assert set_status(conn, food["id"], "discarded") is None  # 되돌리기·재처리 없음
    assert update_food(conn, food["id"], name="a") is None
    assert delete_food(conn, food["id"]) is False
    assert get_food(conn, food["id"], include_processed=True)["status"] == "eaten"


def test_set_status_rejects_none_value(conn):
    food = make(conn)
    with pytest.raises(ValueError):
        set_status(conn, food["id"], "none")


def test_delete_removes_row_completely(conn):
    food = make(conn)
    assert delete_food(conn, food["id"]) is True
    assert conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0] == 0
    assert delete_food(conn, food["id"]) is False


def test_data_survives_reconnect(tmp_path):
    path = tmp_path / "fridge.db"
    c1 = connect_foods(path)
    create_foods_schema(c1)
    food = make(c1)
    c1.close()
    c2 = connect_foods(path)
    assert get_food(c2, food["id"]) == food
    c2.close()
