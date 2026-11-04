"""정보 수정(A5)과 보관 방법 변경(A6). 기한 계산, 기한 다시 적기(409), 확인 순서를 본다.

오늘은 2026-10-30. 규칙표는 실제 값(seed_rules.py): 당근 상온 5·냉장 21·냉동 120 / 양파 상온 30·냉장 60·냉동 180 /
달걀(별칭 계란) 상온 7·냉장 30·냉동 불가 / 두부 냉장 5만 가능 / 우유 냉장 7만 가능.
"""
from datetime import date, timedelta

import psycopg
import pytest

from app.db import foods_repo

PW = "Passw0rd!"
TODAY = date(2026, 10, 30)


def day(offset_from_today: int) -> str:
    return (TODAY + timedelta(days=offset_from_today)).isoformat()


def login(make_client, email="kim@example.com"):
    c = make_client()
    assert c.post("/auth/signup", json={"email": email, "password": PW}).status_code == 201
    return c


@pytest.fixture
def me(make_client):
    return login(make_client)


@pytest.fixture
def other(make_client):
    return login(make_client, "lee@example.com")


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


def add(pg, email="kim@example.com", **over):
    """시험용 식품을 표에 바로 넣는다 (과거 기한처럼 등록으로는 만들 수 없는 것도 넣으려고)."""
    uid = str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])
    data = dict(
        name="당근", storage="fridge", quantity=1, unit="개", purchase_date="2026-10-26",
        expiry_date="2026-11-16", source="rule",
    )
    data.update(over)
    if data["source"] == "manual":
        data.setdefault("category", "other")  # 직접 등록 식품은 종류가 꼭 있어야 한다
    food = foods_repo.create_food(pg, uid, **data)
    pg.commit()
    return food


def stored(pg, food):
    uid = pg.execute("SELECT user_id FROM foods WHERE id = %s", (food["id"],)).fetchone()["user_id"]
    return foods_repo.get_food(pg, str(uid), food["id"], include_processed=True)


def storage(client, food, **body):
    return client.patch(f"/foods/{food['id']}/storage", json=body)


def info(client, food, **body):
    return client.patch(f"/foods/{food['id']}", json=body)


def remaining(purchase_offset, cur, new):
    """새 남은 기간 = (1 − 쓴 기간 ÷ 지금 방법 최대) × 새 방법 최대, 내림. 구매일이 미래면 쓴 기간 0."""
    elapsed = max(-purchase_offset, 0)
    return ((cur - elapsed) * new) // cur


# ======== A6 보관 방법 변경 PATCH /foods/{id}/storage ========
def test_a6_rule_food_recalculates_by_ratio(me, pg):
    # 당근 냉장 21일 중 4일(10/26~10/30) 보관 → 냉동 120일 기준 (1 − 4/21) × 120 = 97.14 → 97일 남음
    food = add(pg)
    response = storage(me, food, storage="freezer")
    assert response.status_code == 200
    body = response.json()
    assert (body["storage"], body["source"]) == ("freezer", "rule")
    assert body["expiry_date"] == day(97) == day(remaining(-4, 21, 120))
    assert (body["expiry_status"], body["days_left"]) == ("fresh", 97)
    assert stored(pg, food)["expiry_date"] == day(97)


def test_a6_fraction_of_a_day_is_rounded_down(me, pg):
    # 당근 상온 5일 중 2일 보관 → 냉장 21일 기준 (1 − 2/5) × 21 = 12.6 → 12일
    food = add(pg, storage="room", purchase_date="2026-10-28", expiry_date="2026-11-02")
    assert storage(me, food, storage="fridge").json()["expiry_date"] == day(12)


def test_a6_future_purchase_gets_the_full_new_period_from_purchase_day(me, pg):
    # 구매일이 미래면 보관한 기간은 0일 (D-022). 구매일(11/02)부터 냉동 120일
    food = add(pg, purchase_date="2026-11-02", expiry_date="2026-11-23")
    assert storage(me, food, storage="freezer").json()["expiry_date"] == (date(2026, 11, 2) + timedelta(days=120)).isoformat()


def test_a6_same_storage_succeeds_changes_nothing_and_ignores_expiry(me, pg):
    food = add(pg)
    before = stored(pg, food)
    for body in ({"storage": "fridge"}, {"storage": "fridge", "expiry_date": "2030-01-01"}):
        response = me.patch(f"/foods/{food['id']}/storage", json=body)
        assert response.status_code == 200 and response.json()["expiry_date"] == "2026-11-16"
    assert stored(pg, food) == before


def test_a6_same_storage_wins_even_for_manual_food(me, pg):
    manual = add(pg, name="수제청", storage="room", source="manual")
    assert storage(me, manual, storage="room").status_code == 200  # 기한을 다시 적게 하지 않는다 (5절 19번)


def test_a6_not_allowed_storage_is_422_and_saves_nothing(me, pg):
    food = add(pg, name="두부", purchase_date="2026-10-28", expiry_date="2026-11-02")
    response = storage(me, food, storage="room")
    assert shape(response) == (422, "storage", "storage_not_allowed")
    assert stored(pg, food) == food


def test_a6_expired_food_changes_when_new_expiry_is_after_today(me, pg):
    # 당근 냉동 120일 중 29일 보관(이미 기한 지남으로 만든 자료) → 냉장 21일 기준 15일 남음 → 기한이 늘어난다
    food = add(pg, storage="freezer", purchase_date="2026-10-01", expiry_date="2026-10-28")
    body = storage(me, food, storage="fridge").json()
    assert body["expiry_date"] == day(remaining(-29, 120, 21)) == day(15)
    assert (body["expiry_status"], body["days_left"]) == ("fresh", 15)  # 더 이상 지남이 아니다


def test_a6_expired_food_is_blocked_when_new_expiry_is_not_after_today(me, pg):
    # 냉장 21일을 21일 다 보관 → 새 남은 기간 0일 → 새 기한이 오늘이라 오늘보다 뒤가 아니다
    food = add(pg, purchase_date="2026-10-09", expiry_date="2026-10-29")
    response = storage(me, food, storage="freezer")
    assert shape(response) == (422, "storage", "storage_change_not_allowed")
    assert stored(pg, food) == food


def test_a6_negative_result_is_blocked(me, pg):
    # 냉장 21일인데 29일 보관: 계산 결과가 음수 → 바꿀 수 없다 (D-006)
    food = add(pg, purchase_date="2026-10-01", expiry_date="2026-10-22")
    assert shape(storage(me, food, storage="freezer")) == (422, "storage", "storage_change_not_allowed")
    assert stored(pg, food) == food


def test_a6_not_yet_expired_food_may_end_today(me, pg):
    # 기한이 오늘인 식품(지남 아님)에서 남은 기간 0일이 나오면 바뀐다. 새 기한은 오늘
    food = add(pg, purchase_date="2026-10-09", expiry_date="2026-10-30")
    body = storage(me, food, storage="freezer").json()
    assert (body["expiry_date"], body["days_left"], body["expiry_status"]) == ("2026-10-30", 0, "soon")


def test_a6_manual_food_must_rewrite_the_expiry(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual", expiry_date="2026-11-05")
    response = storage(me, food, storage="fridge")
    assert shape(response) == (409, "expiry_date", "expiry_required")
    assert response.json()["message"] == "기한을 다시 적어 주세요."
    assert stored(pg, food) == food  # 아무것도 저장하지 않았다

    response = storage(me, food, storage="fridge", expiry_date="2026-12-01")
    assert response.status_code == 200
    body = response.json()
    assert (body["storage"], body["expiry_date"], body["source"]) == ("fridge", "2026-12-01", "manual")


@pytest.mark.parametrize(
    "extra, expected",
    [
        ({"expiry_date": "2026-10-29"}, (422, "expiry_date", "expiry_in_past")),
        ({"expiry_date": "2026-02-30"}, (422, "expiry_date", "invalid_date")),
        ({"expiry_date": "내일"}, (422, "expiry_date", "invalid_date")),
    ],
)
def test_a6_manual_food_new_expiry_errors(me, pg, extra, expected):
    food = add(pg, name="수제청", storage="room", source="manual", expiry_date="2026-11-05")
    assert shape(storage(me, food, storage="fridge", **extra)) == expected
    assert stored(pg, food) == food


def test_a6_manual_food_new_expiry_before_purchase(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual", purchase_date="2026-11-10", expiry_date="2026-11-20")
    assert shape(storage(me, food, storage="fridge", expiry_date="2026-11-05")) == (
        422, "expiry_date", "purchase_after_expiry",
    )


def test_a6_malformed_expiry_is_rejected_even_when_not_needed(me, pg):
    """쓰지 않는 값도 모양은 검사한다 (사용자 결정). 올바른 모양이면 무시한다."""
    food = add(pg)
    assert shape(storage(me, food, storage="freezer", expiry_date="abc")) == (422, "expiry_date", "invalid_date")
    assert storage(me, food, storage="freezer", expiry_date="2030-01-01").json()["expiry_date"] == day(97)  # 무시
    same = add(pg)
    assert shape(storage(me, same, storage="fridge", expiry_date="abc")) == (422, "expiry_date", "invalid_date")


@pytest.mark.parametrize("value", ["shelf", "", None, 3])
def test_a6_invalid_storage(me, pg, value):
    food = add(pg)
    assert shape(me.patch(f"/foods/{food['id']}/storage", json={"storage": value})) == (422, "storage", "invalid_storage")
    assert shape(me.patch(f"/foods/{food['id']}/storage", json={})) == (422, "storage", "invalid_storage")


def test_a6_rule_name_vanished_from_the_rule_table(me, pg):
    food = add(pg)
    pg.execute("DELETE FROM rules WHERE name = '당근'")
    pg.commit()
    response = storage(me, food, storage="freezer")
    assert shape(response) == (422, "storage", "rule_not_found")  # 문서가 정한 방식 (API-SPEC 5절 7번)
    assert response.json()["message"] == "이 식품의 보관 정보를 찾을 수 없어요."
    # 규칙표에서 이름을 찾을 수 없으면 종류는 null, 위험은 아님으로 보인다 (API-SPEC 0-1절). 그 밖의 칸은 그대로다.
    assert stored(pg, food) == {**food, "category": None, "is_danger": False, "danger_note": None}


def test_a6_not_found_cases_and_order(me, other, pg):
    mine = add(pg)
    done = add(pg, name="처리함")
    me.patch(f"/foods/{done['id']}/process", json={"status": "eaten"})
    fake = "0b0e0b8e-3f4b-4f43-9f0a-5d5b0d9b3b11"
    for response in (
        me.patch(f"/foods/{fake}/storage", json={"storage": "shelf"}),  # 식품 확인이 입력 검사보다 먼저다
        me.patch("/foods/abc/storage", json={"storage": "freezer"}),
        me.patch(f"/foods/{done['id']}/storage", json={"storage": "freezer"}),
        other.patch(f"/foods/{mine['id']}/storage", json={"storage": "freezer"}),
    ):
        assert shape(response) == (404, None, "not_found")
    assert stored(pg, mine) == mine


# ======== A5 정보 수정 PATCH /foods/{id} ========
def test_a5_quantity_and_unit_only_keep_expiry_and_status(me, pg):
    food = add(pg)
    response = info(me, food, quantity=2.5, unit="봉")
    assert response.status_code == 200
    body = response.json()
    assert (body["quantity"], body["unit"]) == (2.5, "봉")
    assert {k: body[k] for k in ("name", "purchase_date", "expiry_date", "source", "status", "storage")} == {
        k: food[k] for k in ("name", "purchase_date", "expiry_date", "source", "status", "storage")
    }


def test_a5_unsent_fields_stay_and_empty_body_changes_nothing(me, pg):
    food = add(pg)
    assert info(me, food, unit=" 개 ").json()["unit"] == "개"  # 앞뒤 공백은 지운다
    assert info(me, food).json()["quantity"] == 1
    assert stored(pg, food)["name"] == "당근"


@pytest.mark.parametrize(
    "body, expected",
    [
        ({"name": ""}, (422, "name", "required")),
        ({"name": None}, (422, "name", "required")),
        ({"unit": "  "}, (422, "unit", "required")),
        ({"quantity": 0}, (422, "quantity", "invalid_quantity")),
        ({"quantity": 1.234}, (422, "quantity", "invalid_quantity")),
        ({"quantity": None}, (422, "quantity", "invalid_quantity")),
        ({"quantity": 100000000}, (422, "quantity", "invalid_quantity")),
        ({"purchase_date": "2026-02-30"}, (422, "purchase_date", "invalid_date")),
        ({"purchase_date": None}, (422, "purchase_date", "invalid_date")),
        ({"expiry_date": "abc"}, (422, "expiry_date", "invalid_date")),  # 쓰지 않아도 모양은 검사한다
    ],
)
def test_a5_input_errors_save_nothing(me, pg, body, expected):
    food = add(pg)
    assert shape(info(me, food, **body)) == expected
    assert stored(pg, food) == food


def test_a5_purchase_date_moves_rule_expiry_by_the_same_days(me, pg):
    food = add(pg, name="양파", storage="room", purchase_date="2026-10-30", expiry_date="2026-11-29")
    body = info(me, food, purchase_date="2026-10-25").json()
    assert (body["purchase_date"], body["expiry_date"]) == ("2026-10-25", "2026-11-24")  # 5일 앞으로
    body = info(me, food, purchase_date="2026-12-01").json()  # 미래 날짜도 된다
    assert (body["purchase_date"], body["expiry_date"]) == ("2026-12-01", "2026-12-31")


def test_a5_purchase_date_keeps_manual_expiry_but_cannot_pass_it(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual", purchase_date="2026-10-20", expiry_date="2026-11-05")
    body = info(me, food, purchase_date="2026-11-05").json()  # 같은 날은 괜찮다
    assert (body["purchase_date"], body["expiry_date"]) == ("2026-11-05", "2026-11-05")
    response = info(me, food, purchase_date="2026-11-06")
    assert shape(response) == (422, "purchase_date", "purchase_after_expiry")
    assert stored(pg, food)["purchase_date"] == "2026-11-05"


def test_a5_rename_rule_to_rule_keeps_the_used_ratio(me, pg):
    # 당근 냉장 21일 중 4일 사용 → 양파 냉장 60일 기준 (1 − 4/21) × 60 = 48.57 → 48일 남음
    food = add(pg)
    body = info(me, food, name="양파").json()
    assert (body["name"], body["source"], body["storage"]) == ("양파", "rule", "fridge")
    assert body["expiry_date"] == day(48) == day(remaining(-4, 21, 60))


def test_a5_rename_by_alias_saves_the_official_name(me, pg):
    food = add(pg)  # 당근 냉장 21일 중 4일 → 달걀 냉장 30일
    body = info(me, food, name="계란").json()
    assert body["name"] == "달걀" and body["expiry_date"] == day(remaining(-4, 21, 30))


def test_a5_rename_manual_to_rule_uses_the_period_that_was_written(me, pg):
    # 직접 적은 기간 30일(10/20~11/19) 중 10일 사용 → 당근 냉장 21일 기준 (1 − 10/30) × 21 = 14일
    food = add(pg, name="수제청", source="manual", purchase_date="2026-10-20", expiry_date="2026-11-19")
    body = info(me, food, name="당근").json()
    assert (body["name"], body["source"]) == ("당근", "rule")
    assert body["expiry_date"] == day(14)


def test_a5_rename_manual_with_zero_period_gets_the_whole_new_period(me, pg):
    food = add(pg, name="수제청", source="manual", purchase_date="2026-10-30", expiry_date="2026-10-30")
    assert info(me, food, name="당근").json()["expiry_date"] == day(21)  # 사용자 결정: 새 규칙의 기간 전체


def test_a5_rename_to_rule_name_ignores_a_valid_expiry_date(me, pg):
    food = add(pg)
    assert info(me, food, name="양파", expiry_date="2030-01-01").json()["expiry_date"] == day(48)


def test_a5_rename_to_rule_name_where_current_storage_is_not_allowed(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual")
    response = info(me, food, name="두부")  # 두부는 상온 불가
    assert shape(response) == (422, "storage", "storage_not_allowed")  # DATA-MODEL Q-24 ①
    assert stored(pg, food) == food


def test_a5_rename_to_name_not_in_rules_needs_a_new_expiry(me, pg):
    for source, name in (("rule", "당근"), ("manual", "수제청")):
        food = add(pg, name=name, source=source, expiry_date="2026-11-16")
        response = info(me, food, name="새이름")
        assert shape(response) == (409, "expiry_date", "expiry_required")  # 규칙표 식품이든 직접 등록 식품이든
        assert stored(pg, food) == food  # 아무것도 저장하지 않았다
        body = info(me, food, name="새이름", expiry_date="2026-12-10").json()
        assert (body["name"], body["expiry_date"], body["source"]) == ("새이름", "2026-12-10", "manual")


def test_a5_rename_to_name_not_in_rules_checks_the_new_expiry(me, pg):
    food = add(pg)
    assert shape(info(me, food, name="새이름", expiry_date="2026-10-29")) == (422, "expiry_date", "expiry_in_past")
    future = add(pg, purchase_date="2026-11-10", expiry_date="2026-12-01")
    assert shape(info(me, future, name="새이름", expiry_date="2026-11-05")) == (422, "expiry_date", "purchase_after_expiry")
    assert stored(pg, food) == food and stored(pg, future) == future


def test_a5_expired_food_cannot_get_a_name_outside_the_rules(me, pg):
    food = add(pg, purchase_date="2026-10-01", expiry_date="2026-10-22")
    # 기한을 안 적어도, 적어도 같다 (오늘 이후 날짜를 적는 길이 막혀 있어 다시 적게 해도 소용없다)
    assert shape(info(me, food, name="새이름")) == (422, "name", "rename_expired_not_allowed")
    assert shape(info(me, food, name="새이름", expiry_date="2026-12-01")) == (422, "name", "rename_expired_not_allowed")
    assert stored(pg, food) == food


def test_a5_expired_food_may_get_a_rule_name_and_uses_the_ratio_result(me, pg):
    # 당근 냉장 21일을 29일 사용(10/01~10/30) → 양파 냉장 60일 기준 (21−29)×60÷21 = −22.8 → −23일. 막지 않는다 (사용자 결정)
    food = add(pg, purchase_date="2026-10-01", expiry_date="2026-10-22")
    body = info(me, food, name="양파").json()
    assert body["expiry_date"] == day(remaining(-29, 21, 60)) == day(-23)
    assert (body["expiry_status"], body["days_left"]) == ("expired", -23)


def test_a5_ratio_result_before_the_purchase_date_is_rejected(me, pg):
    food = add(pg, storage="room", purchase_date="2026-10-01", expiry_date="2026-10-06")  # 당근 상온 5일, 29일 사용
    response = info(me, food, name="양파")  # (5−29)×30÷5 = −144일 → 구매일보다 앞
    assert shape(response) == (422, "expiry_date", "purchase_after_expiry")
    assert stored(pg, food) == food


def test_a5_name_and_purchase_date_together_apply_name_first_then_shift(me, pg):
    food = add(pg)  # 당근 냉장 21일 중 4일 사용 → 양파 48일 남음 → 구매일이 2일 늦어지면 기한도 2일 늦어진다
    body = info(me, food, name="양파", purchase_date="2026-10-28").json()
    assert (body["name"], body["purchase_date"], body["expiry_date"]) == ("양파", "2026-10-28", day(48 + 2))


def test_a5_same_name_or_same_official_name_is_not_a_rename(me, pg):
    food = add(pg, name="달걀", storage="fridge", purchase_date="2026-10-26", expiry_date="2026-11-25")
    for name in ("달걀", " 달걀 ", "계란"):
        body = info(me, food, name=name).json()
        assert (body["name"], body["expiry_date"]) == ("달걀", "2026-11-25")  # 기한이 다시 계산되지 않는다


def test_a5_not_found_cases_and_order(me, other, pg):
    mine = add(pg)
    done = add(pg, name="처리함")
    me.patch(f"/foods/{done['id']}/process", json={"status": "discarded"})
    fake = "0b0e0b8e-3f4b-4f43-9f0a-5d5b0d9b3b11"
    for response in (
        me.patch(f"/foods/{fake}", json={"name": ""}),  # 식품 확인이 입력 검사보다 먼저다
        me.patch("/foods/abc", json={"quantity": 1}),
        me.patch(f"/foods/{done['id']}", json={"quantity": 1}),
        other.patch(f"/foods/{mine['id']}", json={"quantity": 99}),
    ):
        assert shape(response) == (404, None, "not_found")
    assert stored(pg, mine) == mine


def test_a5_db_failure_is_server_error_and_changes_nothing(me, pg, monkeypatch):
    food = add(pg)

    def boom(*args, **kwargs):
        raise psycopg.OperationalError("db is down")

    monkeypatch.setattr(foods_repo, "update_food", boom)
    assert shape(info(me, food, quantity=5)) == (500, None, "server_error")
    assert stored(pg, food) == food


def test_a5_a6_need_login(client):
    fake = "0b0e0b8e-3f4b-4f43-9f0a-5d5b0d9b3b11"
    assert shape(client.patch(f"/foods/{fake}", json={})) == (401, None, "login_required")
    assert shape(client.patch(f"/foods/{fake}/storage", json={"storage": "room"})) == (401, None, "login_required")


# ---- 이름을 고칠 때 종류 (DATA-MODEL Q-34, v0.5.0) -------------------------------------------------------
def patch_name(me, food, **body):
    return me.patch(f"/foods/{food['id']}", json=body)


def stored_category(pg, food):
    return pg.execute("SELECT category FROM foods WHERE id = %s", (food["id"],)).fetchone()["category"]


def test_rename_rule_food_to_unknown_name_keeps_the_old_rule_category(me, pg):
    food = add(pg, name="닭고기", storage="fridge", expiry_date="2026-11-16")
    body = patch_name(me, food, name="수제 닭요리", expiry_date="2026-11-20").json()
    assert (body["source"], body["category"], body["is_danger"]) == ("manual", "meat", False)  # 위험 표시는 없어진다 (D-166)
    assert stored_category(pg, food) == "meat"


def test_rename_rule_food_to_unknown_name_when_rule_is_gone_stores_other(me, pg):
    food = add(pg, name="당근")
    pg.execute("DELETE FROM rules WHERE name = '당근'")
    pg.commit()
    body = patch_name(me, food, name="수제 당근", expiry_date="2026-11-20").json()
    assert (body["source"], body["category"]) == ("manual", "other")


def test_rename_manual_food_to_rule_name_clears_the_stored_category(me, pg):
    food = add(pg, name="수제청", source="manual", category="fruit", purchase_date="2026-10-20", expiry_date="2026-11-19")
    body = patch_name(me, food, name="사과").json()
    assert (body["source"], body["category"]) == ("rule", "fruit")  # 이제 규칙표 값(사과는 과일)을 읽어 붙인다
    assert stored_category(pg, food) is None


def test_rename_manual_food_to_unknown_name_keeps_its_category(me, pg):
    food = add(pg, name="수제청", source="manual", category="seafood", expiry_date="2026-11-20")
    body = patch_name(me, food, name="다른 수제청", expiry_date="2026-11-25").json()
    assert (body["source"], body["category"]) == ("manual", "seafood")


def test_plain_edits_do_not_touch_the_category(me, pg):
    food = add(pg, name="수제청", source="manual", category="meat", expiry_date="2026-11-20")
    assert me.patch(f"/foods/{food['id']}", json={"quantity": 3}).json()["category"] == "meat"
    rule_food = add(pg, name="당근")
    assert me.patch(f"/foods/{rule_food['id']}", json={"quantity": 3}).json()["category"] == "vegetable"
    assert stored_category(pg, rule_food) is None


# ======== A5 정보 고치기에 보관 방법·종류를 함께 (v0.5.0, API-SPEC A5, V-39, D-172) ========
def test_a5_storage_in_patch_recalculates_by_ratio_like_the_old_storage_route(me, pg):
    # 당근 냉장 21일 중 4일 보관 → 냉동 120일 기준 97일 남음 (A6 와 같은 계산)
    food = add(pg)
    body = info(me, food, storage="freezer").json()
    assert (body["storage"], body["source"], body["expiry_date"]) == ("freezer", "rule", day(97))
    assert stored(pg, food)["expiry_date"] == day(97)


def test_a5_patch_and_old_storage_route_give_the_same_result(me, pg):
    one, two = add(pg), add(pg)
    assert info(me, one, storage="freezer").json()["expiry_date"] == storage(me, two, storage="freezer").json()["expiry_date"]


def test_a5_same_storage_in_patch_changes_nothing_and_ignores_expiry(me, pg):
    food = add(pg)
    before = stored(pg, food)
    for body in ({"storage": "fridge"}, {"storage": "fridge", "expiry_date": "2030-01-01"}):
        response = info(me, food, **body)
        assert response.status_code == 200 and response.json()["expiry_date"] == "2026-11-16"
    assert stored(pg, food) == before


def test_a5_same_storage_wins_even_for_manual_food_and_does_not_ask_for_an_expiry(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual")
    assert info(me, food, storage="room").status_code == 200  # 기한을 다시 적게 하지 않는다


def test_a5_manual_food_must_rewrite_the_expiry_when_the_storage_changes(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual", expiry_date="2026-11-05")
    response = info(me, food, storage="fridge")
    assert shape(response) == (409, "expiry_date", "expiry_required")
    assert stored(pg, food) == food  # 아무것도 저장하지 않는다
    body = info(me, food, storage="fridge", expiry_date="2026-12-01").json()
    assert (body["storage"], body["expiry_date"], body["source"]) == ("fridge", "2026-12-01", "manual")


@pytest.mark.parametrize(
    "extra, expected",
    [
        ({"expiry_date": "2026-10-29"}, (422, "expiry_date", "expiry_in_past")),
        ({"expiry_date": "2026-10-25"}, (422, "expiry_date", "expiry_in_past")),
        ({"expiry_date": "2026-13-40"}, (422, "expiry_date", "invalid_date")),
    ],
)
def test_a5_manual_food_new_expiry_errors(me, pg, extra, expected):
    food = add(pg, name="수제청", storage="room", source="manual", expiry_date="2026-11-05")
    assert shape(info(me, food, storage="fridge", **extra)) == expected
    assert stored(pg, food) == food


def test_a5_storage_not_allowed_and_bad_value(me, pg):
    egg = add(pg, name="달걀", storage="fridge", expiry_date="2026-11-30")
    assert shape(info(me, egg, storage="freezer")) == (422, "storage", "storage_not_allowed")  # 달걀 냉동 불가
    assert shape(info(me, egg, storage="shelf")) == (422, "storage", "invalid_storage")
    assert shape(info(me, egg, storage=None)) == (422, "storage", "invalid_storage")
    assert stored(pg, egg) == egg


def test_a5_rule_name_vanished_blocks_the_storage_change(me, pg):
    food = add(pg)
    pg.execute("DELETE FROM rules WHERE name = '당근'")
    pg.commit()
    assert shape(info(me, food, storage="freezer")) == (422, "storage", "rule_not_found")


def test_a5_name_then_storage_then_purchase_order(me, pg):
    # 당근(냉장) → 양파(규칙표 이름)로 바꾸고, 그 식품 기준으로 냉동으로 바꾸고, 구매일을 이틀 뒤로 옮긴다.
    food = add(pg, name="당근", storage="fridge", purchase_date="2026-10-26", expiry_date="2026-11-16")
    body = info(me, food, name="양파", storage="freezer", purchase_date="2026-10-28").json()
    assert (body["name"], body["storage"], body["source"], body["purchase_date"]) == ("양파", "freezer", "rule", "2026-10-28")
    # 양파 냉장 60일 → 냉동 180일, 구매일 10/26 에서 4일 보관한 비율을 이어받고, 구매일이 2일 움직여 기한도 2일 뒤로
    expected = date(2026, 10, 30) + timedelta(days=((60 - 4) * 180) // 60) + timedelta(days=2)
    assert body["expiry_date"] == expected.isoformat()


def test_a5_rename_to_unknown_name_and_storage_together_uses_the_written_expiry(me, pg):
    food = add(pg, name="당근", storage="fridge", expiry_date="2026-11-16")
    body = info(me, food, name="수제 당근", storage="freezer", expiry_date="2027-01-15").json()
    assert (body["name"], body["storage"], body["source"], body["expiry_date"]) == ("수제 당근", "freezer", "manual", "2027-01-15")
    assert body["category"] == "vegetable"  # 바뀌기 전 규칙표의 종류 (Q-34)


def test_a5_rename_to_unknown_name_with_storage_still_needs_the_expiry(me, pg):
    food = add(pg, name="당근", storage="fridge", expiry_date="2026-11-16")
    assert shape(info(me, food, name="수제 당근", storage="freezer")) == (409, "expiry_date", "expiry_required")
    assert stored(pg, food) == food


def test_a5_storage_and_purchase_together_for_a_rule_food(me, pg):
    # 보관 방법을 먼저 계산하고(구매일 옛 값 기준), 그 기한을 구매일이 움직인 만큼 옮긴다
    food = add(pg, purchase_date="2026-10-26", expiry_date="2026-11-16")
    body = info(me, food, storage="freezer", purchase_date="2026-10-28").json()
    assert body["expiry_date"] == day(97 + 2)


def test_a5_storage_and_purchase_together_for_a_manual_food(me, pg):
    food = add(pg, name="수제청", storage="room", source="manual", purchase_date="2026-10-20", expiry_date="2026-11-05")
    body = info(me, food, storage="fridge", expiry_date="2026-12-01", purchase_date="2026-10-25").json()
    assert (body["storage"], body["expiry_date"], body["purchase_date"]) == ("fridge", "2026-12-01", "2026-10-25")
    late = info(me, food, storage="room", expiry_date="2026-12-10", purchase_date="2026-12-20")
    assert shape(late) == (422, "expiry_date", "purchase_after_expiry")  # 구매일이 새 기한보다 뒤


def test_a5_expired_food_cannot_change_storage_if_the_new_expiry_is_not_after_today(me, pg):
    # 이미 지난 당근: 냉동 계산 결과가 음수이면 바꿀 수 없다 (V-10)
    food = add(pg, purchase_date="2026-08-01", expiry_date="2026-08-22")
    assert shape(info(me, food, storage="freezer")) == (422, "storage", "storage_change_not_allowed")
    assert stored(pg, food) == food


def test_a5_one_bad_field_saves_nothing_at_all(me, pg):
    food = add(pg)
    response = info(me, food, quantity=5, unit="봉", storage="shelf")  # 수량·단위는 맞지만 보관 방법이 틀렸다
    assert shape(response) == (422, "storage", "invalid_storage")
    assert stored(pg, food) == food
    response = info(me, food, quantity=5, storage="freezer", purchase_date="not-a-date")
    assert shape(response) == (422, "purchase_date", "invalid_date")
    assert stored(pg, food) == food


def test_a5_category_changes_only_for_manual_foods(me, pg):
    manual = add(pg, name="수제청", source="manual", category="other", expiry_date="2026-11-20")
    body = info(me, manual, category="fruit").json()
    assert body["category"] == "fruit" and stored_category(pg, manual) == "fruit"
    assert (body["expiry_date"], body["status"]) == ("2026-11-20", "none")  # 기한과 상태는 그대로
    rule = add(pg)
    body = info(me, rule, category="meat").json()
    assert body["category"] == "vegetable" and stored_category(pg, rule) is None  # 규칙표 식품은 무시한다


@pytest.mark.parametrize("category", [None, "", "snack", "채소", 1])
def test_a5_category_must_be_one_of_five_even_when_it_would_be_ignored(me, pg, category):
    manual = add(pg, name="수제청", source="manual", expiry_date="2026-11-20")
    rule = add(pg)
    for food in (manual, rule):
        assert shape(info(me, food, category=category)) == (422, "category", "invalid_category")
    assert stored(pg, manual)["category"] == "other"


def test_a5_other_accounts_and_processed_foods_are_not_found_for_the_new_fields(me, other, pg):
    mine = add(pg)
    assert shape(info(other, mine, storage="freezer")) == (404, None, "not_found")
    me.patch(f"/foods/{mine['id']}/process", json={"status": "eaten"})
    assert shape(info(me, mine, storage="freezer", category="fruit")) == (404, None, "not_found")


def test_a5_empty_body_changes_nothing(me, pg):
    food = add(pg)
    assert info(me, food).status_code == 200
    assert stored(pg, food) == food


# ---- 이름을 규칙표 이름으로 바꾸면서 보관 방법도 바꿀 때: 바뀐 뒤 보관 방법 기준 (2026-11-04 사용자 결정) -----
def test_a5_rename_to_a_rule_name_that_forbids_the_current_storage_but_the_new_storage_is_fine(me, pg):
    # 당근(냉동 중)을 감자(냉동 불가)로 바꾸면서 냉장으로 바꾼다. 바뀐 뒤 보관 방법(냉장)이 허용이면 저장된다.
    food = add(pg, name="당근", storage="freezer", purchase_date="2026-10-26", expiry_date="2027-02-23")
    body = info(me, food, name="감자", storage="fridge").json()
    assert (body["name"], body["storage"], body["source"]) == ("감자", "fridge", "rule")
    # 당근 냉동 120일 중 4일 보관 → 감자 냉장 30일 기준 (120 − 4) × 30 ÷ 120 = 29일 남음
    assert body["expiry_date"] == day(29)


def test_a5_manual_food_renamed_to_a_rule_name_with_a_new_storage_uses_the_written_period(me, pg):
    # 직접 등록 "수제 계란찜"(냉동, 10/20~11/19 = 30일 잡음)을 달걀(냉동 불가)로 바꾸면서 냉장으로 바꾼다
    food = add(pg, name="수제 계란찜", storage="freezer", source="manual", purchase_date="2026-10-20", expiry_date="2026-11-19")
    body = info(me, food, name="달걀", storage="fridge").json()
    assert (body["name"], body["storage"], body["source"], body["category"]) == ("달걀", "fridge", "rule", "other")
    # 직접 적은 30일 중 10일 보관 → 달걀 냉장 30일 기준 (30 − 10) × 30 ÷ 30 = 20일 남음
    assert body["expiry_date"] == day(20)
    assert stored_category(pg, food) is None  # 규칙표 식품이 되었으므로 저장한 종류는 비운다


def test_a5_rename_to_a_rule_name_still_fails_when_the_new_storage_is_also_forbidden(me, pg):
    food = add(pg, name="당근", storage="freezer", purchase_date="2026-10-26", expiry_date="2027-02-23")
    assert shape(info(me, food, name="감자", storage="freezer")) == (422, "storage", "storage_not_allowed")
    assert shape(info(me, food, name="감자")) == (422, "storage", "storage_not_allowed")  # 보관 방법을 안 바꾸면 그대로 거절
    assert stored(pg, food) == food


def test_a5_rename_with_a_forbidden_new_storage_for_the_new_name_saves_nothing(me, pg):
    food = add(pg, name="당근", storage="freezer", purchase_date="2026-10-26", expiry_date="2027-02-23")
    assert shape(info(me, food, name="달걀", storage="freezer", quantity=9)) == (422, "storage", "storage_not_allowed")
    assert stored(pg, food) == food
