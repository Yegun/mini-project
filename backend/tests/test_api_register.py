from app import repo_foods

# 규칙표 값은 conftest 의 시험용 가짜 값이다: 두부(냉장 10일, 냉동 30일, 상온 불가), 당근(상온 7일 ...).


def error_body(response):
    body = response.json()
    assert set(body) == {"field", "reason", "message"}
    return body["field"], body["reason"]


def saved_count(conn):
    return conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]


# ---- A2 규칙표 검색 GET /rules?q= ----
def test_a2_finds_by_name_containing_the_word(client):
    response = client.get("/rules", params={"q": "두"})
    assert response.status_code == 200
    assert response.json() == {
        "rules": [
            {
                "name": "두부",
                "aliases": ["연두부"],
                "default_storage": "fridge",
                "not_allowed": ["room"],
            }
        ]
    }


def test_a2_finds_by_alias_and_shows_the_rule_name(client):
    rules = client.get("/rules", params={"q": "연두"}).json()["rules"]
    assert [rule["name"] for rule in rules] == ["두부"]


def test_a2_no_result_is_an_empty_list_not_an_error(client):
    response = client.get("/rules", params={"q": "없는식품"})
    assert response.status_code == 200
    assert response.json() == {"rules": []}


def test_a2_does_not_fix_typos(client):
    assert client.get("/rules", params={"q": "두무"}).json() == {"rules": []}


def test_a2_blank_or_missing_word_is_422(client):
    for params in ({"q": ""}, {"q": "   "}, {}):
        response = client.get("/rules", params=params)
        assert response.status_code == 422
        assert error_body(response)[0] == "q"


def test_a2_does_not_show_period_numbers(client):
    rule = client.get("/rules", params={"q": "두부"}).json()["rules"][0]
    assert "storages" not in rule and "max_days" not in rule


# ---- A3 규칙표 식품 등록 POST /foods ----
RULE_BODY = {
    "name": "두부",
    "quantity": 2,
    "unit": "모",
    "purchase_date": "2026-10-30",
    "storage": "fridge",
}


def test_a3_creates_with_expiry_from_the_rule(client, conn):
    response = client.post("/foods", json=RULE_BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "두부"
    assert body["expiry_date"] == "2026-11-09"  # 구매일 10/30 + 냉장 10일
    assert body["source"] == "rule"
    assert body["status"] == "none"
    assert body["days_left"] == 10
    assert body["expiry_status"] == "fresh"
    assert len(body["id"]) == 36
    assert repo_foods.get_food(conn, body["id"])["name"] == "두부"


def test_a3_expiry_follows_the_chosen_storage(client):
    body = client.post("/foods", json={**RULE_BODY, "storage": "freezer"}).json()
    assert body["expiry_date"] == "2026-11-29"  # 냉동 30일


def test_a3_future_purchase_and_decimal_quantity_are_allowed(client):
    response = client.post(
        "/foods", json={**RULE_BODY, "purchase_date": "2026-11-05", "quantity": 0.25}
    )
    assert response.status_code == 201
    assert response.json()["expiry_date"] == "2026-11-15"
    assert response.json()["quantity"] == 0.25


def test_a3_same_name_can_be_registered_again(client, conn):
    client.post("/foods", json=RULE_BODY)
    client.post("/foods", json=RULE_BODY)
    assert saved_count(conn) == 2


def test_a3_name_not_in_rules_is_422(client, conn):
    for name in ("없는식품", "연두부"):  # 별칭이 아니라 규칙표의 이름을 그대로 보낸다
        response = client.post("/foods", json={**RULE_BODY, "name": name})
        assert response.status_code == 422
        assert error_body(response) == ("name", "not_in_rules")
    assert saved_count(conn) == 0


def test_a3_not_allowed_storage_is_422(client, conn):
    response = client.post("/foods", json={**RULE_BODY, "storage": "room"})
    assert response.status_code == 422
    assert error_body(response) == ("storage", "not_allowed")
    assert saved_count(conn) == 0


def test_a3_input_errors_save_nothing(client, conn):
    cases = [
        ({"name": ""}, ("name", "required")),
        ({"unit": "  "}, ("unit", "required")),
        ({"quantity": 0}, ("quantity", "not_positive")),
        ({"quantity": -2}, ("quantity", "not_positive")),
        ({"quantity": 1.234}, ("quantity", "too_many_decimals")),
        ({"quantity": "2"}, ("quantity", "invalid")),
        ({"purchase_date": "2026-02-30"}, ("purchase_date", "invalid")),
        ({"purchase_date": None}, ("purchase_date", "required")),
        ({"storage": "shelf"}, ("storage", "invalid")),
        ({"storage": None}, ("storage", "required")),
    ]
    for change, expected in cases:
        response = client.post("/foods", json={**RULE_BODY, **change})
        assert response.status_code == 422, change
        assert error_body(response) == expected, change
    assert saved_count(conn) == 0


def test_a3_missing_or_extra_fields_use_the_same_error_shape(client, conn):
    without_unit = {key: value for key, value in RULE_BODY.items() if key != "unit"}
    assert error_body(client.post("/foods", json=without_unit)) == ("unit", "required")
    assert error_body(client.post("/foods", json={**RULE_BODY, "x": 1})) == ("x", "invalid")
    assert saved_count(conn) == 0


# ---- A4 직접 등록 POST /foods/manual ----
MANUAL_BODY = {
    "name": "수제청",
    "storage": "room",
    "quantity": 1,
    "unit": "병",
    "purchase_date": "2026-10-30",
    "expiry_date": "2026-11-05",
}


def test_a4_creates_with_the_given_expiry_date(client, conn):
    response = client.post("/foods/manual", json=MANUAL_BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["expiry_date"] == "2026-11-05"
    assert body["source"] == "manual"
    assert body["status"] == "none"
    assert body["storage"] == "room"  # 직접 등록은 세 방법 모두 고를 수 있다
    assert repo_foods.get_food(conn, body["id"])["source"] == "manual"


def test_a4_days_later_is_purchase_date_plus_n(client):
    body = {k: v for k, v in MANUAL_BODY.items() if k != "expiry_date"}
    response = client.post("/foods/manual", json={**body, "expiry_in_days": 3})
    assert response.status_code == 201
    assert response.json()["expiry_date"] == "2026-11-02"
    response = client.post("/foods/manual", json={**body, "expiry_in_days": 0})
    assert response.json()["expiry_date"] == "2026-10-30"


def test_a4_all_three_storages_are_allowed(client):
    for storage in ("room", "fridge", "freezer"):
        response = client.post("/foods/manual", json={**MANUAL_BODY, "storage": storage})
        assert response.status_code == 201


def test_a4_expiry_errors_save_nothing(client, conn):
    only_days = {k: v for k, v in MANUAL_BODY.items() if k != "expiry_date"}
    cases = [
        (only_days, ("expiry_date", "required")),  # 기한을 안 적음
        ({**MANUAL_BODY, "expiry_in_days": 3}, ("expiry_date", "invalid")),  # 둘 다 적음
        ({**MANUAL_BODY, "expiry_date": "2026-10-29"}, ("expiry_date", "in_past")),
        ({**only_days, "purchase_date": "2026-10-01", "expiry_in_days": 5}, ("expiry_date", "in_past")),
        ({**MANUAL_BODY, "purchase_date": "2026-11-10"}, ("purchase_date", "after_expiry")),
        ({**only_days, "expiry_in_days": -1}, ("expiry_date", "invalid")),
        ({**only_days, "expiry_in_days": 1.5}, ("expiry_date", "invalid")),
        ({**MANUAL_BODY, "expiry_date": "내일"}, ("expiry_date", "invalid")),
    ]  # fmt: skip
    for body, expected in cases:
        response = client.post("/foods/manual", json=body)
        assert response.status_code == 422, body
        assert error_body(response) == expected, body
    assert saved_count(conn) == 0


def test_a4_input_errors_save_nothing(client, conn):
    cases = [
        ({"name": ""}, ("name", "required")),
        ({"unit": ""}, ("unit", "required")),
        ({"quantity": 0}, ("quantity", "not_positive")),
        ({"storage": "shelf"}, ("storage", "invalid")),
        ({"purchase_date": "2026-13-01"}, ("purchase_date", "invalid")),
    ]
    for change, expected in cases:
        response = client.post("/foods/manual", json={**MANUAL_BODY, **change})
        assert response.status_code == 422, change
        assert error_body(response) == expected, change
    assert saved_count(conn) == 0
