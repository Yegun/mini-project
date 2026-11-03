"""규칙표 (PostgreSQL). 실제 30개 값(seed_rules.py)으로 채우기·검색·읽기 전용 계정을 본다."""
import uuid

import psycopg
import pytest
from psycopg import sql

from app import db  # noqa: F401  (패키지 확인)
from app.db import seed_rules as seed_module
from app.db.rules_repo import add_rule, find_rule, get_rule, get_rule_by_name, list_rules, search_rules
from app.db.seed_rules import RULES, check_rules, rule_id_for, seed_rules
from app.db.setup_roles import setup_app_role


def test_seed_fills_30_rules_with_storage_rows(pg_rules):
    assert len(list_rules(pg_rules)) == 30 == len(RULES)
    for rule in list_rules(pg_rules):
        assert [s["storage"] for s in rule["storages"]] == ["room", "fridge", "freezer"]


def test_seed_twice_gives_same_result(pg_rules):
    before = list_rules(pg_rules)
    seed_rules(pg_rules)
    pg_rules.commit()
    assert list_rules(pg_rules) == before


def test_rule_ids_come_from_names(pg_rules):
    assert get_rule_by_name(pg_rules, "양파")["id"] == rule_id_for("양파")


def test_default_storage_is_always_allowed(pg_rules):
    for rule in list_rules(pg_rules):
        chosen = next(s for s in rule["storages"] if s["storage"] == rule["default_storage"])
        assert chosen["allowed"] and chosen["max_days"] > 0


def test_disallowed_has_no_days(pg_rules):
    milk = get_rule_by_name(pg_rules, "우유")
    by = {s["storage"]: s for s in milk["storages"]}
    assert by["room"] == {"storage": "room", "allowed": False, "max_days": None}
    assert by["fridge"]["allowed"] and by["fridge"]["max_days"] == 7


def test_search_by_name_alias_and_partial(pg_rules):
    assert [r["name"] for r in search_rules(pg_rules, "양")] == ["양배추", "양파"]  # 이름순(글자 코드)
    assert [r["name"] for r in search_rules(pg_rules, "계란")] == ["달걀"]  # 별칭으로 찾아도 식품 이름
    assert [r["name"] for r in search_rules(pg_rules, "호박")] == ["애호박"]
    assert [r["name"] for r in search_rules(pg_rules, " 우유 ")] == ["우유"]


def test_search_returns_each_rule_once(pg_rules):
    # 이름과 별칭 양쪽에 걸려도 한 번만 나온다 ("고기" 는 이름 3개, 별칭 "쇠고기" 포함)
    names = [r["name"] for r in search_rules(pg_rules, "고기")]
    assert len(names) == len(set(names)) == 3


def test_search_empty_or_no_match_is_empty_list(pg_rules):
    assert search_rules(pg_rules, "") == []
    assert search_rules(pg_rules, "   ") == []
    assert search_rules(pg_rules, "없는식품") == []  # 오타 보정은 없다


def test_search_percent_and_underscore_are_literal(pg_rules):
    assert search_rules(pg_rules, "%") == []
    assert search_rules(pg_rules, "_") == []


def test_find_rule_by_name_or_alias(pg_rules):
    assert find_rule(pg_rules, "달걀")["name"] == "달걀"
    assert find_rule(pg_rules, "계란")["name"] == "달걀"  # 별칭 → 정식 이름의 규칙 (API-SPEC 5절 20번)
    assert find_rule(pg_rules, "계") is None  # 정확히 같아야 한다
    assert get_rule_by_name(pg_rules, "계란") is None  # 정식 이름만


def test_get_rule(pg_rules):
    rule = get_rule_by_name(pg_rules, "당근")
    assert get_rule(pg_rules, rule["id"]) == rule
    assert get_rule(pg_rules, str(uuid.uuid4())) is None
    assert get_rule(pg_rules, "not-a-uuid") is None


def test_db_rejects_bad_rule_values(pg_rules):
    rid = rule_id_for("양파")
    with pytest.raises(psycopg.errors.CheckViolation):  # 가능인데 일수가 없다
        pg_rules.execute("UPDATE rule_storage SET max_days = NULL WHERE rule_id = %s AND storage = 'room'", (rid,))
    pg_rules.rollback()
    with pytest.raises(psycopg.errors.CheckViolation):  # 불가인데 일수가 있다
        pg_rules.execute(
            "UPDATE rule_storage SET allowed = false WHERE rule_id = %s AND storage = 'room'", (rid,)
        )
    pg_rules.rollback()
    with pytest.raises(psycopg.errors.UniqueViolation):  # 별칭은 중복 불가
        pg_rules.execute("INSERT INTO rule_aliases VALUES (%s, '계란')", (rid,))


def test_deleting_rule_deletes_aliases_and_storage(pg_rules):
    rid = rule_id_for("달걀")
    pg_rules.execute("DELETE FROM rules WHERE id = %s", (rid,))
    for table in ("rule_aliases", "rule_storage"):
        assert pg_rules.execute(f"SELECT count(*) AS n FROM {table} WHERE rule_id = %s", (rid,)).fetchone()["n"] == 0


# ---- 채우기 전 검사 (Q-15) ------------------------------------------------------------------
def test_check_rules_passes_for_real_values():
    check_rules()


def test_check_rules_rejects_default_storage_not_allowed(monkeypatch):
    monkeypatch.setattr(seed_module, "RULES", [("가", "room", None, 5, None, ())])
    with pytest.raises(ValueError, match="기본 보관 방법"):
        check_rules()


def test_check_rules_rejects_alias_equal_to_other_name(monkeypatch):
    rules = [("가", "room", 5, 5, 5, ()), ("나", "room", 5, 5, 5, ("가",))]
    monkeypatch.setattr(seed_module, "RULES", rules)
    with pytest.raises(ValueError, match="다른 식품의 이름"):
        check_rules()


def test_check_rules_rejects_duplicate_alias(monkeypatch):
    rules = [("가", "room", 5, 5, 5, ("x",)), ("나", "room", 5, 5, 5, ("x",))]
    monkeypatch.setattr(seed_module, "RULES", rules)
    with pytest.raises(ValueError, match="두 번"):
        check_rules()


def test_bad_seed_changes_nothing(pg_rules, monkeypatch):
    before = list_rules(pg_rules)
    monkeypatch.setattr(seed_module, "RULES", [("가", "room", None, 5, None, ())])
    with pytest.raises(ValueError):
        seed_rules(pg_rules)
    assert list_rules(pg_rules) == before


# ---- 앱 계정은 규칙표에 읽기와 '더하기'만 한다 (Q-27) -------------------------------------------
def test_app_role_can_read_and_add_but_not_change_rules(pg_url, pg_schema, pg_rules):
    role = "app_t_" + uuid.uuid4().hex[:8]
    password = uuid.uuid4().hex
    admin = psycopg.connect(pg_url, autocommit=True)
    try:
        try:
            admin.execute(sql.SQL("SELECT 1"))
            setup_app_role(admin, role, password, pg_schema)
        except psycopg.errors.InsufficientPrivilege:
            pytest.skip("시험 DB 계정에 계정(ROLE)을 만들 권한이 없다")
        info = psycopg.conninfo.conninfo_to_dict(pg_url)
        info.update(user=role, password=password, options=f"-c search_path={pg_schema}")
        app = psycopg.connect(**info, autocommit=True)
        try:
            # 표 8개에 RLS 가 켜져 있어도(정책 없음) 앱 계정은 RLS 를 건너뛰어 줄을 읽는다 (Q-33)
            assert app.execute("SELECT count(*) FROM rules").fetchone()[0] == 30
            # 규칙표 식품·보관 방법별 정보는 더할 수 있다 (사진으로 한꺼번에 등록, D-136)
            app.execute("INSERT INTO rules (id, name, default_storage) VALUES (gen_random_uuid(), 'x', 'room')")
            app.execute(
                "INSERT INTO rule_storage (rule_id, storage, allowed, max_days)"
                " SELECT id, 'room', true, 3 FROM rules WHERE name = 'x'"
            )
            # 이미 있는 줄을 고치거나 지우는 것, 별칭을 더하거나 고치거나 지우는 것은 못 한다
            for statement in (
                "UPDATE rules SET default_storage = 'room'",
                "DELETE FROM rules",
                "UPDATE rule_storage SET max_days = 1",
                "DELETE FROM rule_storage",
                "INSERT INTO rule_aliases (rule_id, alias) SELECT id, 'xx' FROM rules WHERE name = 'x'",
                "UPDATE rule_aliases SET alias = 'y'",
                "DELETE FROM rule_aliases",
            ):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    app.execute(statement)
            # 식품·계정·로그인 상태 표는 쓸 수 있다
            app.execute("INSERT INTO users (email, password_hash) VALUES ('r@example.com', 'x')")
            # 사진 읽기 결과 표도 쓸 수 있다
            app.execute("INSERT INTO photo_analyses (user_id, items) SELECT id, '[]'::jsonb FROM users")
            app.execute("DELETE FROM photo_analyses")
            # 가입·로그인이 첫 계정 기록(legacy_migration)을 읽고 고친다 (D-097)
            app.execute("SELECT migrated FROM legacy_migration").fetchall()
            app.execute("UPDATE legacy_migration SET migrated = migrated")
            # 표를 만들거나 지울 수는 없다
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                app.execute("DROP TABLE foods")
        finally:
            app.close()
    finally:
        admin.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role)))
        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
        admin.close()


# ---- 규칙표에 더하기 (D-136, Q-27, Q-30) -----------------------------------------------------
def storages(room=None, fridge=5, freezer=None):
    days = {"room": room, "fridge": fridge, "freezer": freezer}
    return [{"storage": s, "allowed": d is not None, "max_days": d} for s, d in days.items()]


def test_add_rule_creates_rule_and_three_storage_rows_without_alias(pg_rules):
    assert add_rule(pg_rules, "닭가슴살", "fridge", storages(fridge=3, freezer=90)) is True
    rule = get_rule_by_name(pg_rules, "닭가슴살")
    assert rule["default_storage"] == "fridge"
    assert [s["storage"] for s in rule["storages"]] == ["room", "fridge", "freezer"]
    assert [(s["allowed"], s["max_days"]) for s in rule["storages"]] == [(False, None), (True, 3), (True, 90)]
    assert pg_rules.execute("SELECT count(*) AS n FROM rule_aliases WHERE rule_id = %s", (rule["id"],)).fetchone()["n"] == 0
    assert len(list_rules(pg_rules)) == 31


def test_added_rule_id_comes_from_the_name(pg_rules):
    add_rule(pg_rules, "닭가슴살", "fridge", storages())
    assert get_rule_by_name(pg_rules, "닭가슴살")["id"] == rule_id_for("닭가슴살")  # 처음 30개와 같은 방식 (Q-30)


def test_added_rule_can_be_found_by_name_only(pg_rules):
    add_rule(pg_rules, "닭가슴살", "fridge", storages())
    assert [r["name"] for r in search_rules(pg_rules, "닭가")] == ["닭가슴살"]
    assert find_rule(pg_rules, "닭가슴살")["name"] == "닭가슴살"


def test_add_rule_does_not_touch_an_existing_name(pg_rules):
    before = get_rule_by_name(pg_rules, "양파")
    assert add_rule(pg_rules, "양파", "fridge", storages(fridge=1)) is False  # 이미 있으면 덮어쓰지 않는다 (D-135)
    assert get_rule_by_name(pg_rules, "양파") == before


def test_add_rule_ignores_a_name_that_is_another_rules_alias(pg_rules):
    assert add_rule(pg_rules, "계란", "fridge", storages()) is False  # 달걀의 별칭
    assert get_rule_by_name(pg_rules, "계란") is None and len(list_rules(pg_rules)) == 30


def test_add_same_name_twice_keeps_the_first(pg_rules):
    assert add_rule(pg_rules, "닭가슴살", "fridge", storages(fridge=3)) is True
    assert add_rule(pg_rules, "닭가슴살", "fridge", storages(fridge=9)) is False  # 먼저 저장된 값이 남는다
    assert get_rule_by_name(pg_rules, "닭가슴살")["storages"][1]["max_days"] == 3


def test_add_rule_rejects_bad_values_and_changes_nothing(pg_rules):
    bad = [{"storage": "room", "allowed": True, "max_days": None}] + storages()[1:]  # 가능인데 일수가 없다
    with pytest.raises(psycopg.errors.CheckViolation):
        add_rule(pg_rules, "닭가슴살", "fridge", bad)
    pg_rules.rollback()
    assert get_rule_by_name(pg_rules, "닭가슴살") is None


def test_add_rule_does_not_commit_by_itself(pg_rules):
    add_rule(pg_rules, "닭가슴살", "fridge", storages())
    pg_rules.rollback()
    assert get_rule_by_name(pg_rules, "닭가슴살") is None


def test_seed_does_not_commit_by_itself(pg):
    seed_rules(pg)
    pg.rollback()
    assert pg.execute("SELECT count(*) AS n FROM rules").fetchone()["n"] == 0
