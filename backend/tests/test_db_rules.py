import sqlite3

import pytest

from app.db import init_db as init_module
from app.db.connection import connect_foods, connect_rules
from app.db.rules_repo import get_rule, get_rule_by_name, list_rules, search_rules
from app.db.schema import create_rules_schema
from app.db.seed_rules import RULES, seed_rules

EXPECTED_NAMES = {
    "양파", "대파", "감자", "당근", "양배추", "오이", "상추", "시금치", "마늘", "애호박", "토마토", "배추", "버섯",
    "사과", "바나나", "딸기", "귤", "포도", "배",
    "돼지고기", "소고기", "닭고기",
    "고등어", "오징어", "새우", "연어",
    "달걀", "우유", "두부", "콩나물",
}


@pytest.fixture
def conn(tmp_path):
    c = connect_rules(tmp_path / "rules.db", readonly=False)
    create_rules_schema(c)
    seed_rules(c)
    yield c
    c.close()


def test_thirty_foods_with_confirmed_names(conn):
    assert {r["name"] for r in list_rules(conn)} == EXPECTED_NAMES
    assert len(RULES) == 30


def test_every_food_has_three_storage_rows_and_default_is_allowed(conn):
    for rule in list_rules(conn):
        assert [s["storage"] for s in rule["storages"]] == ["room", "fridge", "freezer"]
        default = next(s for s in rule["storages"] if s["storage"] == rule["default_storage"])
        assert default["allowed"] is True and default["max_days"] > 0
        for s in rule["storages"]:
            assert (s["max_days"] is None) == (not s["allowed"])


def test_search_by_name_contains(conn):
    names = [r["name"] for r in search_rules(conn, "양")]
    assert names == ["양배추", "양파"]


def test_search_by_alias_returns_food_name_once(conn):
    result = search_rules(conn, "계란")
    assert [r["name"] for r in result] == ["달걀"]


def test_search_no_result_and_blank_query(conn):
    assert search_rules(conn, "망고") == []
    assert search_rules(conn, "   ") == []


def test_search_treats_percent_literally(conn):
    assert search_rules(conn, "%") == []


def test_search_result_includes_default_and_disallowed(conn):
    milk = search_rules(conn, "우유")[0]
    assert milk["default_storage"] == "fridge"
    assert [s["allowed"] for s in milk["storages"]] == [False, True, False]


def test_get_by_name_exact_only(conn):
    assert get_rule_by_name(conn, "양파")["name"] == "양파"
    assert get_rule_by_name(conn, "양") is None
    assert get_rule_by_name(conn, "계란") is None  # 별칭은 이름이 아니다
    rule = get_rule_by_name(conn, "양파")
    assert get_rule(conn, rule["id"]) == rule


def test_rule_ids_are_stable_across_reseed(conn):
    before = {r["name"]: r["id"] for r in list_rules(conn)}
    seed_rules(conn)
    assert {r["name"]: r["id"] for r in list_rules(conn)} == before


def test_db_rejects_inconsistent_storage_rows(conn):
    rid = get_rule_by_name(conn, "양파")["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO rule_storage VALUES (?, 'room', 1, NULL)", (rid,))  # 가능인데 일수 없음
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO rule_storage VALUES (?, 'room', 0, 5)", (rid,))  # 불가인데 일수 있음


def test_readonly_connection_cannot_write(tmp_path):
    path = tmp_path / "rules.db"
    w = connect_rules(path, readonly=False)
    create_rules_schema(w)
    seed_rules(w)
    w.close()
    r = connect_rules(path)
    assert len(list_rules(r)) == 30
    with pytest.raises(sqlite3.OperationalError):
        r.execute("DELETE FROM rules")
    r.close()


def test_init_db_twice_same_result_and_keeps_foods(tmp_path, monkeypatch):
    monkeypatch.setenv("FRIDGE_DB_PATH", str(tmp_path / "f" / "fridge.db"))
    monkeypatch.setenv("RULES_DB_PATH", str(tmp_path / "f" / "rules.db"))
    init_module.init_db()
    foods = connect_foods()
    foods.execute(
        "INSERT INTO foods VALUES ('00000000-0000-4000-8000-000000000000', '양파', 'room', 1, '개',"
        " '2026-10-30', '2026-11-30', 'rule', 'none')"
    )
    foods.commit()
    foods.close()

    init_module.init_db()  # 두 번째

    rules = connect_rules()
    assert len(list_rules(rules)) == 30
    rules.close()
    foods = connect_foods()
    assert foods.execute("SELECT COUNT(*) FROM foods").fetchone()[0] == 1
    foods.close()
