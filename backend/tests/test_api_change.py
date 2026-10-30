from datetime import date
from decimal import Decimal

from app import repo_foods

# 오늘은 2026-10-30. 규칙표는 conftest 의 시험용 가짜 값:
# 두부(냉장 10, 냉동 30, 상온 불가) / 당근(상온 7, 냉장 20, 냉동 60) / 우유(냉장 7만 가능)


def add_food(conn, **overrides):
    values = {
        "name": "당근",
        "storage": "fridge",
        "quantity": Decimal("1"),
        "unit": "개",
        "purchase_date": date(2026, 10, 26),
        "expiry_date": date(2026, 11, 15),
        "source": "rule",
    }
    values.update(overrides)
    food = repo_foods.create_food(conn, **values)
    conn.commit()
    return food


def error_body(response):
    body = response.json()
    assert set(body) == {"field", "reason", "message"}
    return body["field"], body["reason"]


def stored(conn, food):
    return repo_foods.get_food(conn, food["id"])


# ======== A7 보관 방법 변경 PATCH /foods/{id}/storage ========
def change_storage(client, food, **body):
    return client.patch(f"/foods/{food['id']}/storage", json=body)


def test_a7_rule_food_recalculates_by_ratio(client, conn):
    # 냉장 20일 중 4일 보관 -> 냉동 60일 기준 (1 - 4/20) * 60 = 48일 남음
    food = add_food(conn)
    response = change_storage(client, food, storage="freezer")
    assert response.status_code == 200
    body = response.json()
    assert body["storage"] == "freezer"
    assert body["expiry_date"] == "2026-12-17"  # 오늘 10/30 + 48일
    assert body["source"] == "rule"
    assert stored(conn, food)["expiry_date"] == date(2026, 12, 17)


def test_a7_fraction_of_a_day_is_rounded_down(client, conn):
    # 상온 7일 중 2일 보관 -> 냉장 20일 기준 (1 - 2/7) * 20 = 14.28 -> 14일
    food = add_food(
        conn, storage="room", purchase_date=date(2026, 10, 28), expiry_date=date(2026, 11, 4)
    )
    body = change_storage(client, food, storage="fridge").json()
    assert body["expiry_date"] == "2026-11-13"


def test_a7_future_purchase_gets_the_full_new_period_from_purchase_day(client, conn):
    # 구매일이 미래면 보관한 기간은 0일 (D-022). 구매일부터 세어 11/02 + 60일
    food = add_food(
        conn, purchase_date=date(2026, 11, 2), expiry_date=date(2026, 11, 22)
    )
    body = change_storage(client, food, storage="freezer").json()
    assert body["expiry_date"] == "2027-01-01"


def test_a7_same_storage_succeeds_and_changes_nothing(client, conn):
    food = add_food(conn)
    response = change_storage(client, food, storage="fridge")
    assert response.status_code == 200
    assert response.json()["expiry_date"] == "2026-11-15"
    assert stored(conn, food) == food


def test_a7_not_allowed_storage_is_422(client, conn):
    food = add_food(conn, name="두부", expiry_date=date(2026, 11, 5))
    response = change_storage(client, food, storage="room")
    assert response.status_code == 422
    assert error_body(response) == ("storage", "not_allowed")
    assert stored(conn, food) == food


def test_a7_expired_food_can_change_when_new_expiry_is_after_today(client, conn):
    # 지난 식품도 같은 식을 쓴다. 냉동 60일 중 10일 보관 -> 냉장 20일 기준 16일 남음 -> 기한이 늘어난다
    food = add_food(
        conn,
        storage="freezer",
        purchase_date=date(2026, 10, 20),
        expiry_date=date(2026, 10, 28),
    )
    response = change_storage(client, food, storage="fridge")
    assert response.status_code == 200
    body = response.json()
    assert body["expiry_date"] == "2026-11-15"
    assert body["expiry_status"] == "fresh"  # 더 이상 지남이 아니다
    assert body["days_left"] == 16


def test_a7_expired_food_is_blocked_when_new_expiry_is_not_after_today(client, conn):
    # 냉장 20일을 20일 다 보관 -> 새 남은 기간 0일 -> 새 기한이 오늘이라 오늘보다 뒤가 아니다
    food = add_food(
        conn, purchase_date=date(2026, 10, 10), expiry_date=date(2026, 10, 28)
    )
    response = change_storage(client, food, storage="freezer")
    assert response.status_code == 422
    assert error_body(response) == ("storage", "change_blocked")
    assert stored(conn, food) == food


def test_a7_negative_result_is_blocked(client, conn):
    # 상온 7일인데 20일 보관: 계산 결과가 음수 -> 바꿀 수 없다 (D-006)
    food = add_food(
        conn,
        storage="room",
        purchase_date=date(2026, 10, 10),
        expiry_date=date(2026, 11, 5),
    )
    response = change_storage(client, food, storage="fridge")
    assert response.status_code == 422
    assert error_body(response) == ("storage", "change_blocked")
    assert stored(conn, food) == food


def test_a7_manual_food_must_rewrite_the_expiry(client, conn):
    food = add_food(
        conn, name="수제청", storage="room", source="manual", expiry_date=date(2026, 11, 5)
    )
    response = change_storage(client, food, storage="fridge")
    assert response.status_code == 409
    assert error_body(response) == ("expiry_date", "expiry_required")
    assert stored(conn, food) == food  # 아무것도 저장하지 않았다

    response = change_storage(client, food, storage="fridge", expiry_date="2026-12-01")
    assert response.status_code == 200
    body = response.json()
    assert body["storage"] == "fridge"
    assert body["expiry_date"] == "2026-12-01"
    assert body["source"] == "manual"


def test_a7_manual_food_new_expiry_cannot_be_in_the_past_or_before_purchase(client, conn):
    food = add_food(
        conn, name="수제청", storage="room", source="manual", expiry_date=date(2026, 11, 5)
    )
    response = change_storage(client, food, storage="fridge", expiry_date="2026-10-29")
    assert (response.status_code, error_body(response)) == (422, ("expiry_date", "in_past"))
    response = change_storage(client, food, storage="fridge", expiry_date="2026-10-25")
    assert response.status_code == 422  # 오늘보다 과거
    future = add_food(
        conn,
        name="수제청",
        storage="room",
        source="manual",
        purchase_date=date(2026, 11, 10),
        expiry_date=date(2026, 11, 12),
    )
    response = change_storage(client, future, storage="fridge", expiry_date="2026-11-05")
    assert (response.status_code, error_body(response)) == (422, ("purchase_date", "after_expiry"))
    assert stored(conn, food) == food


def test_a7_manual_food_same_storage_needs_no_expiry(client, conn):
    food = add_food(conn, name="수제청", storage="room", source="manual")
    response = change_storage(client, food, storage="room")
    assert response.status_code == 200


def test_a7_rule_food_does_not_take_an_expiry(client, conn):
    food = add_food(conn)
    response = change_storage(client, food, storage="freezer", expiry_date="2026-12-01")
    assert (response.status_code, error_body(response)) == (422, ("expiry_date", "invalid"))
    assert stored(conn, food) == food


def test_a7_bad_storage_value(client, conn):
    food = add_food(conn)
    response = change_storage(client, food, storage="shelf")
    assert (response.status_code, error_body(response)) == (422, ("storage", "invalid"))
    response = client.patch(f"/foods/{food['id']}/storage", json={})
    assert (response.status_code, error_body(response)) == (422, ("storage", "required"))


def test_a7_missing_or_processed_food(client, conn):
    response = client.patch("/foods/없는-번호/storage", json={"storage": "freezer"})
    assert (response.status_code, error_body(response)) == (404, (None, "not_found"))
    food = add_food(conn)
    repo_foods.set_status(conn, food["id"], "eaten")
    conn.commit()
    response = change_storage(client, food, storage="freezer")
    assert (response.status_code, error_body(response)) == (409, (None, "already_processed"))


# ======== A6 정보 수정 PATCH /foods/{id} ========
def edit(client, food, **body):
    return client.patch(f"/foods/{food['id']}", json=body)


def test_a6_quantity_and_unit_only_change_those(client, conn):
    food = add_food(conn)
    response = edit(client, food, quantity=2.5, unit="봉지")
    assert response.status_code == 200
    body = response.json()
    assert (body["quantity"], body["unit"]) == (2.5, "봉지")
    assert body["expiry_date"] == "2026-11-15"  # 기한과 상태는 그대로
    assert body["name"] == "당근"
    assert stored(conn, food)["unit"] == "봉지"


def test_a6_empty_body_changes_nothing(client, conn):
    food = add_food(conn)
    response = edit(client, food)
    assert response.status_code == 200
    assert stored(conn, food) == food


def test_a6_same_name_does_not_recalculate(client, conn):
    food = add_food(conn)
    response = edit(client, food, name="당근")
    assert response.status_code == 200
    assert stored(conn, food) == food


def test_a6_purchase_date_moves_a_rule_food_expiry_by_the_same_days(client, conn):
    food = add_food(conn)  # 구매일 10/26, 기한 11/15
    body = edit(client, food, purchase_date="2026-10-28").json()
    assert body["purchase_date"] == "2026-10-28"
    assert body["expiry_date"] == "2026-11-17"  # 구매일이 2일 뒤로 -> 기한도 2일 뒤로 (D-024)


def test_a6_purchase_date_keeps_a_manual_expiry(client, conn):
    food = add_food(
        conn,
        name="수제청",
        source="manual",
        purchase_date=date(2026, 10, 26),
        expiry_date=date(2026, 11, 5),
    )
    body = edit(client, food, purchase_date="2026-11-01").json()
    assert body["expiry_date"] == "2026-11-05"  # 직접 적은 기한은 그대로
    response = edit(client, food, purchase_date="2026-11-10")
    assert (response.status_code, error_body(response)) == (422, ("purchase_date", "after_expiry"))
    assert stored(conn, food)["purchase_date"] == date(2026, 11, 1)


def test_a6_rename_to_another_rule_keeps_the_used_ratio(client, conn):
    # 두부 냉장 10일 중 5일 보관(50%) -> 당근 냉장 20일 기준 10일 남음 -> 10/30 + 10
    food = add_food(
        conn,
        name="두부",
        purchase_date=date(2026, 10, 25),
        expiry_date=date(2026, 11, 4),
    )
    body = edit(client, food, name="당근").json()
    assert body["name"] == "당근"
    assert body["expiry_date"] == "2026-11-09"
    assert body["source"] == "rule"


def test_a6_rename_manual_food_to_a_rule_name(client, conn):
    # 직접 정한 20일(10/20~11/09) 중 10일 보관(50%) -> 두부 냉장 10일 기준 5일 남음 (사용자 결정)
    food = add_food(
        conn,
        name="수제청",
        source="manual",
        purchase_date=date(2026, 10, 20),
        expiry_date=date(2026, 11, 9),
    )
    body = edit(client, food, name="두부").json()
    assert body["expiry_date"] == "2026-11-04"
    assert body["source"] == "rule"  # 규칙표 식품으로 바뀐다


def test_a6_rename_manual_food_with_zero_period_to_a_rule_name(client, conn):
    food = add_food(
        conn,
        name="수제청",
        source="manual",
        purchase_date=date(2026, 10, 30),
        expiry_date=date(2026, 10, 30),
    )
    body = edit(client, food, name="두부").json()
    assert body["expiry_date"] == "2026-10-30"
    assert body["source"] == "rule"


def test_a6_rename_to_a_rule_that_does_not_allow_the_current_storage(client, conn):
    food = add_food(conn, storage="room", expiry_date=date(2026, 11, 2))  # 상온 당근
    response = edit(client, food, name="우유")  # 우유는 상온 불가
    assert (response.status_code, error_body(response)) == (422, ("storage", "not_allowed"))
    assert stored(conn, food) == food


def test_a6_rename_an_expired_rule_food_to_another_rule_is_allowed(client, conn):
    # 당근 냉장 20일을 29일 보관(이미 지남) -> 두부 냉장 10일 기준 (1 - 29/20) * 10 = -4.5 -> -5일
    food = add_food(
        conn, purchase_date=date(2026, 10, 1), expiry_date=date(2026, 10, 21)
    )
    body = edit(client, food, name="두부").json()
    assert body["expiry_date"] == "2026-10-25"
    assert body["expiry_status"] == "expired"
    assert body["days_left"] == -5


def test_a6_rename_to_a_name_not_in_rules_needs_a_new_expiry(client, conn):
    food = add_food(
        conn, name="두부", purchase_date=date(2026, 10, 25), expiry_date=date(2026, 11, 4)
    )
    response = edit(client, food, name="수제두부")
    assert response.status_code == 409
    assert error_body(response) == ("expiry_date", "expiry_required")
    assert stored(conn, food) == food

    response = edit(client, food, name="수제두부", expiry_date="2026-11-20")
    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["expiry_date"], body["source"]) == ("수제두부", "2026-11-20", "manual")


def test_a6_new_expiry_cannot_be_in_the_past_or_before_the_purchase(client, conn):
    food = add_food(
        conn, name="두부", purchase_date=date(2026, 10, 25), expiry_date=date(2026, 11, 4)
    )
    response = edit(client, food, name="수제두부", expiry_date="2026-10-29")
    assert (response.status_code, error_body(response)) == (422, ("expiry_date", "in_past"))
    response = edit(client, food, name="수제두부", expiry_date="2026-11-20", purchase_date="2026-11-25")
    assert (response.status_code, error_body(response)) == (422, ("purchase_date", "after_expiry"))
    assert stored(conn, food) == food


def test_a6_expired_food_cannot_be_renamed_to_a_name_not_in_rules(client, conn):
    food = add_food(conn, expiry_date=date(2026, 10, 28))
    response = edit(client, food, name="수제당근", expiry_date="2026-12-01")
    assert response.status_code == 422
    assert error_body(response) == ("name", "name_change_blocked")
    assert stored(conn, food) == food


def test_a6_expiry_without_a_name_change_is_rejected(client, conn):
    food = add_food(conn)
    response = edit(client, food, expiry_date="2026-12-01")
    assert (response.status_code, error_body(response)) == (422, ("expiry_date", "invalid"))
    response = edit(client, food, name="두부", expiry_date="2026-12-01")  # 규칙표 이름이면 기한은 계산된다
    assert (response.status_code, error_body(response)) == (422, ("expiry_date", "invalid"))
    assert stored(conn, food) == food


def test_a6_name_and_purchase_date_together_rename_first(client, conn):
    # 이름 변경을 먼저 처리(기한 11/09), 그 기한에 구매일 이동(+2일)을 적용 -> 11/11 (D-026)
    food = add_food(
        conn, name="두부", purchase_date=date(2026, 10, 25), expiry_date=date(2026, 11, 4)
    )
    body = edit(client, food, name="당근", purchase_date="2026-10-27").json()
    assert body["name"] == "당근"
    assert body["purchase_date"] == "2026-10-27"
    assert body["expiry_date"] == "2026-11-11"


def test_a6_input_errors_save_nothing(client, conn):
    food = add_food(conn)
    cases = [
        ({"name": ""}, ("name", "required")),
        ({"name": None}, ("name", "required")),
        ({"unit": " "}, ("unit", "required")),
        ({"quantity": 0}, ("quantity", "not_positive")),
        ({"quantity": 1.234}, ("quantity", "too_many_decimals")),
        ({"purchase_date": "2026-02-30"}, ("purchase_date", "invalid")),
        ({"x": 1}, ("x", "invalid")),
    ]
    for body, expected in cases:
        response = edit(client, food, **body)
        assert response.status_code == 422, body
        assert error_body(response) == expected, body
    assert stored(conn, food) == food


def test_a6_rule_food_whose_rule_disappeared_is_a_server_error(client, conn):
    food = add_food(conn, name="사라진식품")
    response = edit(client, food, name="두부")
    assert (response.status_code, error_body(response)) == (500, (None, "load_failed"))
    assert stored(conn, food) == food


def test_a6_missing_or_processed_food(client, conn):
    response = client.patch("/foods/없는-번호", json={"unit": "개"})
    assert (response.status_code, error_body(response)) == (404, (None, "not_found"))
    food = add_food(conn)
    repo_foods.set_status(conn, food["id"], "discarded")
    conn.commit()
    response = edit(client, food, unit="개")
    assert (response.status_code, error_body(response)) == (409, (None, "already_processed"))
