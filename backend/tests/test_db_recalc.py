"""규칙표를 고친 뒤 기한 다시 계산 (PostgreSQL). 대상, 건너뛰기, 되돌리기(rollback), 여러 번 실행을 본다."""
from conftest import food_args

from app.db import seed_rules as seed_module
from app.db.foods_repo import create_food, get_food, set_status
from app.db.recalc_expiry import recalc_expiry
from app.db.seed_rules import seed_rules


def add(pg, user, **over):
    return create_food(pg, user["id"], **food_args(**over))


def expiry(pg, user, food):
    return get_food(pg, user["id"], food["id"], include_processed=True)["expiry_date"]


def test_up_to_date_foods_stay_the_same(pg_rules, two_users):
    a, _ = two_users
    add(pg_rules, a, name="양파", storage="room", purchase_date="2026-10-30", expiry_date="2026-11-29")  # 상온 30일
    result = recalc_expiry(pg_rules)
    assert result == {"changed": [], "same": 1, "skipped": []}


def test_changed_rule_days_move_expiry_for_all_accounts(pg_rules, two_users, monkeypatch):
    a, b = two_users
    food_a = add(pg_rules, a, name="양파", storage="room", purchase_date="2026-10-30", expiry_date="2026-11-29")
    food_b = add(pg_rules, b, name="양파", storage="fridge", purchase_date="2026-10-01", expiry_date="2026-11-30")
    rules = [(n, d, 40 if n == "양파" else r, f, z, al) for n, d, r, f, z, al in seed_module.RULES]
    monkeypatch.setattr(seed_module, "RULES", rules)
    seed_rules(pg_rules)

    result = recalc_expiry(pg_rules)
    assert result["changed"] == [("양파", "2026-10-30", "2026-11-29", "2026-12-09")]  # 상온 30 → 40일
    assert result["same"] == 1  # 냉장 60일은 그대로
    assert expiry(pg_rules, a, food_a) == "2026-12-09"
    assert expiry(pg_rules, b, food_b) == "2026-11-30"


def test_manual_and_processed_foods_are_untouched(pg_rules, two_users, monkeypatch):
    a, _ = two_users
    manual = add(pg_rules, a, name="양파", source="manual", expiry_date="2026-11-05")
    done = add(pg_rules, a, name="양파", storage="room")
    set_status(pg_rules, a["id"], done["id"], "eaten", "2026-11-02")
    rules = [(n, d, 99 if n == "양파" else r, f, z, al) for n, d, r, f, z, al in seed_module.RULES]
    monkeypatch.setattr(seed_module, "RULES", rules)
    seed_rules(pg_rules)

    assert recalc_expiry(pg_rules) == {"changed": [], "same": 0, "skipped": []}
    assert expiry(pg_rules, a, manual) == "2026-11-05"
    assert expiry(pg_rules, a, done) == "2026-11-29"


def test_skips_unknown_name_and_now_disallowed_storage(pg_rules, two_users, monkeypatch):
    a, _ = two_users
    add(pg_rules, a, name="없어진식품", storage="room")
    add(pg_rules, a, name="양파", storage="freezer", purchase_date="2026-10-30", expiry_date="2027-04-28")
    rules = [(n, d, r, f, None if n == "양파" else z, al) for n, d, r, f, z, al in seed_module.RULES]
    monkeypatch.setattr(seed_module, "RULES", rules)
    seed_rules(pg_rules)

    result = recalc_expiry(pg_rules)
    assert result["changed"] == [] and result["same"] == 0
    assert [(n, why) for n, _, why in result["skipped"]] == [
        ("양파", "지금 보관 방법이 규칙표에서 불가"),
        ("없어진식품", "규칙표에 없는 이름"),
    ]  # 구매일이 같으면 이름순(글자 코드)


def test_dry_run_saves_nothing_and_second_run_is_stable(pg_rules, two_users, monkeypatch):
    a, _ = two_users
    food = add(pg_rules, a, name="양파", storage="room", purchase_date="2026-10-30", expiry_date="2026-11-29")
    rules = [(n, d, 40 if n == "양파" else r, f, z, al) for n, d, r, f, z, al in seed_module.RULES]
    monkeypatch.setattr(seed_module, "RULES", rules)
    seed_rules(pg_rules)

    dry = recalc_expiry(pg_rules, dry_run=True)
    assert len(dry["changed"]) == 1 and expiry(pg_rules, a, food) == "2026-11-29"
    first = recalc_expiry(pg_rules)
    second = recalc_expiry(pg_rules)
    assert len(first["changed"]) == 1 and second == {"changed": [], "same": 1, "skipped": []}
