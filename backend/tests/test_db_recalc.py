import sqlite3

import pytest

from app.db import init_db as init_module
from app.db import recalc_expiry as recalc_module
from app.db.connection import connect_foods, connect_rules
from app.db.foods_repo import create_food, get_food, set_status
from app.db.recalc_expiry import recalc_expiry
from app.db.schema import create_foods_schema, create_rules_schema
from app.db.seed_rules import rule_id_for, seed_rules


@pytest.fixture
def dbs(tmp_path):
    """식품 DB 와 규칙표 DB 한 쌍. 규칙표는 개발용 임시값(당근 냉장 21, 우유 냉장 7)이다."""
    rules_path = tmp_path / "rules.db"
    foods = connect_foods(tmp_path / "fridge.db")
    create_foods_schema(foods)
    w = connect_rules(rules_path, readonly=False)
    create_rules_schema(w)
    seed_rules(w)
    w.commit()
    w.close()
    rules = connect_rules(rules_path)  # 읽기 전용
    yield foods, rules, rules_path
    foods.close()
    rules.close()


def make(foods, **over):
    data = dict(
        name="당근", storage="fridge", quantity=1, unit="개",
        purchase_date="2026-10-25", expiry_date="2026-11-15", source="rule",
    )
    data.update(over)
    return create_food(foods, **data)


def edit_rules(path, sql, *args):
    w = connect_rules(path, readonly=False)
    with w:
        w.execute(sql, args)
    w.close()


def test_changed_rule_value_moves_rule_food_expiry(dbs):
    foods, rules, path = dbs
    food = make(foods)  # 구매일 10-25 + 21일 = 11-15
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    result = recalc_expiry(foods, connect_rules(path))
    assert result["changed"] == [("당근", "2026-10-25", "2026-11-15", "2026-11-24")]  # 10-25 + 30
    assert get_food(foods, food["id"])["expiry_date"] == "2026-11-24"


def test_unchanged_rule_values_change_nothing(dbs):
    foods, rules, _ = dbs
    food = make(foods)
    result = recalc_expiry(foods, rules)
    assert result == {"changed": [], "same": 1, "skipped": []}
    assert get_food(foods, food["id"])["expiry_date"] == "2026-11-15"


def test_manual_food_is_left_alone(dbs):
    foods, _, path = dbs
    food = make(foods, name="수제잼", source="manual", expiry_date="2026-12-01")
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    result = recalc_expiry(foods, connect_rules(path))
    assert result == {"changed": [], "same": 0, "skipped": []}
    assert get_food(foods, food["id"])["expiry_date"] == "2026-12-01"


def test_manual_food_with_a_rule_name_is_left_alone(dbs):
    # source 가 기준이다. 이름이 규칙표와 같아도 직접 등록 기한은 그대로 둔다.
    foods, _, path = dbs
    food = make(foods, source="manual", expiry_date="2026-12-01")
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    recalc_expiry(foods, connect_rules(path))
    assert get_food(foods, food["id"])["expiry_date"] == "2026-12-01"


def test_processed_food_is_left_alone(dbs):
    foods, _, path = dbs
    food = make(foods)
    set_status(foods, food["id"], "eaten")
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    result = recalc_expiry(foods, connect_rules(path))
    assert result == {"changed": [], "same": 0, "skipped": []}
    assert get_food(foods, food["id"], include_processed=True)["expiry_date"] == "2026-11-15"


def test_food_whose_storage_became_not_allowed_is_skipped_and_reported(dbs):
    foods, _, path = dbs
    food = make(foods, name="우유", expiry_date="2026-11-01")
    edit_rules(
        path,
        "UPDATE rule_storage SET allowed = 0, max_days = NULL WHERE rule_id = ? AND storage = 'fridge'",
        rule_id_for("우유"),
    )
    result = recalc_expiry(foods, connect_rules(path))
    assert result["changed"] == [] and result["skipped"] == [("우유", "2026-10-25", "지금 보관 방법이 규칙표에서 불가")]
    assert get_food(foods, food["id"])["expiry_date"] == "2026-11-01"


def test_food_whose_name_is_not_in_rules_is_skipped_and_reported(dbs):
    foods, rules, _ = dbs
    make(foods, name="없는이름")
    result = recalc_expiry(foods, rules)
    assert result["skipped"] == [("없는이름", "2026-10-25", "규칙표에 없는 이름")]


def test_each_food_uses_its_own_storage(dbs):
    foods, _, path = dbs
    a = make(foods, storage="fridge")  # 냉장 21 -> 30
    b = make(foods, storage="freezer", expiry_date="2027-02-22")  # 냉동 120 -> 그대로
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    recalc_expiry(foods, connect_rules(path))
    assert get_food(foods, a["id"])["expiry_date"] == "2026-11-24"
    assert get_food(foods, b["id"])["expiry_date"] == "2027-02-22"


def test_dry_run_saves_nothing(dbs):
    foods, _, path = dbs
    food = make(foods)
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    result = recalc_expiry(foods, connect_rules(path), dry_run=True)
    assert len(result["changed"]) == 1
    assert get_food(foods, food["id"])["expiry_date"] == "2026-11-15"


def test_all_or_nothing_when_one_update_fails(dbs):
    foods, _, path = dbs
    ok = make(foods)
    make(foods, name="당근", purchase_date="2026-10-26", expiry_date="2026-11-16", unit="실패")
    foods.execute(
        "CREATE TRIGGER fail_one BEFORE UPDATE ON foods WHEN OLD.unit = '실패'"
        " BEGIN SELECT RAISE(ABORT, 'boom'); END"
    )
    foods.commit()
    edit_rules(path, "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))
    with pytest.raises(sqlite3.DatabaseError):
        recalc_expiry(foods, connect_rules(path))
    assert get_food(foods, ok["id"])["expiry_date"] == "2026-11-15"  # 앞의 한 건도 되돌려졌다


def test_rules_db_is_only_read(dbs):
    foods, rules, _ = dbs
    make(foods)
    recalc_expiry(foods, rules)
    with pytest.raises(sqlite3.OperationalError):
        rules.execute("DELETE FROM rules")


def test_command_runs_on_the_real_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FRIDGE_DB_PATH", str(tmp_path / "fridge.db"))
    monkeypatch.setenv("RULES_DB_PATH", str(tmp_path / "rules.db"))
    init_module.init_db()
    foods = connect_foods()
    food = make(foods)
    foods.close()
    edit_rules(tmp_path / "rules.db", "UPDATE rule_storage SET max_days = 30 WHERE rule_id = ? AND storage = 'fridge'", rule_id_for("당근"))

    assert recalc_module.main(["--dry-run"]) == 0
    assert "바뀔 식품 1건" in capsys.readouterr().out
    foods = connect_foods()
    assert get_food(foods, food["id"])["expiry_date"] == "2026-11-15"
    foods.close()

    assert recalc_module.main([]) == 0
    assert "바꾼 식품 1건" in capsys.readouterr().out
    foods = connect_foods()
    assert get_food(foods, food["id"])["expiry_date"] == "2026-11-24"
    foods.close()

    # 두 번째는 바뀔 것이 없다
    assert recalc_module.main([]) == 0
    assert "바꾼 식품 0건, 그대로 1건" in capsys.readouterr().out


def test_command_stops_when_db_files_are_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FRIDGE_DB_PATH", str(tmp_path / "none.db"))
    monkeypatch.setenv("RULES_DB_PATH", str(tmp_path / "none2.db"))
    assert recalc_module.main([]) == 1
    assert "init_db" in capsys.readouterr().out
    assert not (tmp_path / "none.db").exists()  # 없는 파일을 새로 만들지 않는다
