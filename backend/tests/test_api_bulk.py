"""한꺼번에 등록 (API-SPEC F2, US-019, US-020). PostgreSQL 임시 schema 에서 서버 코드를 그대로 지난다."""
import pytest

from app.db import foods_repo, photo_analyses_repo, rules_repo
from app.db.seed_rules import rule_id_for

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}
OTHER = {"email": "lee@example.com", "password": "Other1234!"}


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


def user_id(pg, email=CRED["email"]):
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])


def storages(room=None, fridge=None, freezer=None):
    days = {"room": room, "fridge": fridge, "freezer": freezer}
    return [{"storage": s, "allowed": d is not None, "max_days": d} for s, d in days.items()]


# F1 이 보관하는 읽기 결과의 줄 (DATA-MODEL 6절). 우유는 규칙표에 있는 식품, 닭가슴살·김치는 AI 가 알려 준 새 식품이다.
READ_ITEMS = [
    {"item_no": 0, "name": "닭가슴살", "recommended_storage": "fridge", "storages": storages(fridge=3, freezer=90),
     "purchase_date": "2026-10-28", "from_rule": False},
    {"item_no": 1, "name": "우유", "recommended_storage": "fridge", "storages": storages(fridge=7, freezer=30),
     "purchase_date": "2026-10-28", "from_rule": True},
    {"item_no": 2, "name": "김치", "recommended_storage": "fridge", "storages": storages(room=2, fridge=60),
     "purchase_date": "2026-10-28", "from_rule": False},
]


def line(item_no=0, name="닭가슴살", **over):
    data = {"item_no": item_no, "name": name, "quantity": 2, "unit": "팩", "purchase_date": "2026-10-28", "storage": "fridge"}
    data.update(over)
    return {k: v for k, v in data.items() if v is not ...}


def count(pg, table, where="", *params):
    return pg.execute(f"SELECT count(*) AS n FROM {table} {where}", params).fetchone()["n"]


@pytest.fixture
def me(client, pg):
    assert client.post("/auth/signup", json=CRED).status_code == 201
    return user_id(pg)


@pytest.fixture
def analysis(me, pg):
    """로그인한 계정의 읽기 결과 한 줄. 번호를 돌려준다."""
    analysis_id = photo_analyses_repo.save_analysis(pg, me, READ_ITEMS)
    pg.commit()
    return analysis_id


def post(client, analysis_id, items):
    return client.post("/foods/bulk", json={"analysis_id": analysis_id, "items": items})


def foods_of(pg, uid):
    return foods_repo.list_active_foods(pg, uid)


# ---- 로그인 · 요청 전체 ------------------------------------------------------------------------
def test_login_required(make_client, analysis):
    anonymous = make_client()  # 로그인하지 않은 다른 기기
    assert shape(post(anonymous, analysis, [line()])) == (401, None, "login_required")


@pytest.mark.parametrize("items", [None, [], "닭가슴살", {}, 3])
def test_items_must_be_a_non_empty_list(client, analysis, items):
    assert shape(post(client, analysis, items)) == (422, "items", "required")


def test_items_check_comes_before_the_analysis_check(client, me):
    assert shape(post(client, None, [])) == (422, "items", "required")  # API-SPEC F2 의 오류 순서


@pytest.mark.parametrize("bad", [None, "", "not-a-uuid", 12345, ["x"], {"a": 1}, "00000000-0000-0000-0000-000000000000"])
def test_missing_or_unknown_analysis_id_is_analysis_expired(client, me, analysis, bad):
    response = post(client, bad, [line()])
    assert shape(response) == (422, None, "analysis_expired")
    assert response.json()["message"] == "사진을 다시 올려 주세요."


def test_body_without_analysis_id_cannot_register(client, me, analysis):
    assert shape(client.post("/foods/bulk", json={"items": [line()]})) == (422, None, "analysis_expired")  # 5절 31번


def test_another_accounts_analysis_is_the_same_as_a_missing_one(client, make_client, me, pg, analysis):
    other = make_client()
    other.post("/auth/signup", json=OTHER)
    assert shape(post(other, analysis, [line()])) == (422, None, "analysis_expired")  # 남의 번호 (D-063)
    assert photo_analyses_repo.get_valid_analysis(pg, me, analysis) is not None  # 남의 요청이 내 결과를 지우지 않는다


def test_expired_analysis_is_removed_and_cannot_register(client, me, pg, analysis):
    pg.execute("UPDATE photo_analyses SET created_at = clock_timestamp() - interval '31 minutes'")
    pg.commit()
    assert shape(post(client, analysis, [line()])) == (422, None, "analysis_expired")
    assert count(pg, "photo_analyses") == 0  # 만료된 줄은 지운 채로 남는다 (DATA-MODEL 6절)
    assert foods_of(pg, me) == []


def test_29_minutes_old_analysis_still_works(client, me, pg, analysis):
    pg.execute("UPDATE photo_analyses SET created_at = clock_timestamp() - interval '29 minutes'")
    pg.commit()
    assert post(client, analysis, [line()]).status_code == 201


# ---- 성공: 규칙표에 없는 이름 · 있는 이름 ------------------------------------------------------------
def test_new_food_is_registered_as_a_rule_food_and_added_to_the_rule_table(client, me, pg, analysis):
    response = post(client, analysis, [line(0, "닭가슴살", quantity=1.5, unit="kg", storage="freezer")])
    assert response.status_code == 201
    [food] = response.json()["items"]
    assert (food["name"], food["storage"], food["quantity"], food["unit"], food["source"], food["status"]) == (
        "닭가슴살", "freezer", 1.5, "kg", "rule", "none")
    assert food["purchase_date"] == "2026-10-28" and food["expiry_date"] == "2027-01-26"  # 구매일 + 냉동 90일 (AI 값)
    assert food["processed_date"] is None and food["expiry_status"] == "fresh" and "user_id" not in food

    rule = rules_repo.get_rule_by_name(pg, "닭가슴살")  # 규칙표에 더해졌다 (D-136)
    assert rule["id"] == rule_id_for("닭가슴살") and rule["default_storage"] == "fridge"
    assert rule["storages"] == storages(fridge=3, freezer=90)
    assert count(pg, "rule_aliases", "WHERE rule_id = %s", rule["id"]) == 0  # 별칭은 만들지 않는다


def test_food_whose_name_is_already_in_the_rule_table_uses_the_rule_values_and_adds_nothing(client, me, pg_rules, analysis):
    before = len(rules_repo.list_rules(pg_rules))
    [food] = post(client, analysis, [line(1, "우유", storage="fridge")]).json()["items"]
    assert food["source"] == "rule" and food["expiry_date"] == "2026-11-04"  # 규칙표 냉장 7일
    assert len(rules_repo.list_rules(pg_rules)) == before


def test_rule_table_wins_over_the_saved_ai_values_if_the_name_has_been_added_in_the_meantime(client, me, pg, analysis):
    rules_repo.add_rule(pg, "닭가슴살", "freezer", storages(fridge=5, freezer=200))  # 다른 계정이 먼저 더했다
    pg.commit()
    [food] = post(client, analysis, [line(0, "닭가슴살", storage="fridge")]).json()["items"]
    assert food["expiry_date"] == "2026-11-02"  # 먼저 저장된 규칙표 값 5일 (D-135)
    assert rules_repo.get_rule_by_name(pg, "닭가슴살")["storages"] == storages(fridge=5, freezer=200)  # 덮어쓰지 않았다


def test_several_lines_register_in_order_and_each_new_food_is_added_once(client, me, pg_rules, analysis):
    response = post(client, analysis, [line(2, "김치", storage="room", quantity=1), line(0, "닭가슴살"), line(1, "우유", quantity=3)])
    assert response.status_code == 201
    assert [f["name"] for f in response.json()["items"]] == ["김치", "닭가슴살", "우유"]  # 보낸 줄 순서대로 (5절 26번)
    assert [f["expiry_date"] for f in response.json()["items"]] == ["2026-10-30", "2026-10-31", "2026-11-04"]
    assert len(rules_repo.list_rules(pg_rules)) == 32  # 김치·닭가슴살만 더해졌다 (우유는 이미 있다)


def test_foods_belong_to_me_and_only_me(client, make_client, me, pg, analysis):
    post(client, analysis, [line(0), line(2, "김치")])
    other = make_client()
    other.post("/auth/signup", json=OTHER)
    assert len(foods_of(pg, me)) == 2 and foods_of(pg, user_id(pg, OTHER["email"])) == []
    assert other.get("/foods").json()["items"] == []


def test_same_name_lines_are_registered_separately(client, me, pg):
    # 영수증에 같은 식품이 두 번 적혀 읽은 결과에 이름이 같은 줄이 둘이다. 따로 등록되고 규칙표에는 한 번만 더해진다 (D-030)
    twice = [dict(READ_ITEMS[0], item_no=0), dict(READ_ITEMS[0], item_no=1)]
    analysis_id = photo_analyses_repo.save_analysis(pg, me, twice)
    pg.commit()
    response = post(client, analysis_id, [line(0, "닭가슴살", quantity=1), line(1, "닭가슴살", quantity=4, storage="freezer")])
    assert response.status_code == 201 and [f["quantity"] for f in response.json()["items"]] == [1, 4]
    assert [f["expiry_date"] for f in response.json()["items"]] == ["2026-10-31", "2027-01-26"]
    assert count(pg, "foods", "WHERE name = '닭가슴살'") == 2 and count(pg, "rules", "WHERE name = '닭가슴살'") == 1


def test_renaming_to_a_name_that_only_another_line_adds_is_a_manual_line(client, me, pg, analysis):
    # 김치 줄을 닭가슴살로 고쳤다. 닭가슴살은 아직 규칙표에 없으므로(같은 등록에서 더해지는 중) 기한을 직접 적어야 한다
    response = post(client, analysis, [line(0, "닭가슴살"), line(2, "닭가슴살")])
    assert shape(response) == (422, "items.1.expiry_date", "expiry_input_invalid")
    assert foods_of(pg, me) == [] and rules_repo.get_rule_by_name(pg, "닭가슴살") is None


def test_lines_the_user_removed_are_neither_registered_nor_added_to_the_rule_table(client, me, pg, analysis):
    post(client, analysis, [line(0, "닭가슴살")])  # 김치(item_no 2)는 확인 단계에서 뺐다
    assert rules_repo.get_rule_by_name(pg, "김치") is None
    assert [f["name"] for f in foods_of(pg, me)] == ["닭가슴살"]


def test_a_used_analysis_is_removed(client, me, pg, analysis):
    post(client, analysis, [line(0)])
    assert photo_analyses_repo.get_valid_analysis(pg, me, analysis) is None and count(pg, "photo_analyses") == 0


def test_registering_the_same_request_twice_registers_once(client, me, pg, analysis):
    assert post(client, analysis, [line(0)]).status_code == 201
    assert shape(post(client, analysis, [line(0)])) == (422, None, "analysis_expired")  # 연타해도 한 번만 (D-112)
    assert len(foods_of(pg, me)) == 1


def test_future_purchase_date_is_allowed(client, me, analysis):
    [food] = post(client, analysis, [line(0, purchase_date="2026-12-01")]).json()["items"]
    assert food["purchase_date"] == "2026-12-01" and food["expiry_date"] == "2026-12-04"


# ---- 이름을 고친 줄 -------------------------------------------------------------------------------
def test_renamed_to_a_rule_table_name_uses_the_rule_values(client, me, pg_rules, analysis):
    before = len(rules_repo.list_rules(pg_rules))
    [food] = post(client, analysis, [line(0, "양파", storage="room")]).json()["items"]  # 닭가슴살 → 양파
    assert (food["name"], food["source"], food["expiry_date"]) == ("양파", "rule", "2026-11-27")  # 상온 30일
    assert rules_repo.get_rule_by_name(pg_rules, "닭가슴살") is None  # AI 가 읽은 이름의 값은 새 이름에 붙이지 않는다
    assert len(rules_repo.list_rules(pg_rules)) == before


def test_renamed_to_an_alias_is_stored_under_the_official_name(client, me, analysis):
    [food] = post(client, analysis, [line(0, "계란", storage="fridge")]).json()["items"]
    assert food["name"] == "달걀" and food["source"] == "rule"


def test_renamed_line_checks_the_new_names_disallowed_storage(client, me, analysis):
    assert shape(post(client, analysis, [line(0, "우유", storage="room")])) == (422, "items.0.storage", "storage_not_allowed")


def test_renamed_to_unknown_name_needs_an_expiry_and_is_a_manual_food(client, me, pg, analysis):
    response = post(client, analysis, [line(0, "수제 닭가슴살", expiry_date="2026-11-20", storage="room")])
    [food] = response.json()["items"]
    assert (food["name"], food["source"], food["expiry_date"], food["storage"]) == ("수제 닭가슴살", "manual", "2026-11-20", "room")
    assert rules_repo.get_rule_by_name(pg, "수제 닭가슴살") is None and rules_repo.get_rule_by_name(pg, "닭가슴살") is None  # 규칙표에 더하지 않는다


def test_manual_line_can_use_days_from_purchase(client, me, analysis):
    [food] = post(client, analysis, [line(0, "수제 닭가슴살", expiry_in_days=10)]).json()["items"]
    assert food["expiry_date"] == "2026-11-07"  # 구매일 + 10일 (D-002)


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({}, (422, "items.0.expiry_date", "expiry_input_invalid")),  # 기한을 안 보냄
        ({"expiry_date": "2026-11-20", "expiry_in_days": 5}, (422, "items.0.expiry_date", "expiry_input_invalid")),  # 둘 다
        ({"expiry_date": "내일"}, (422, "items.0.expiry_date", "invalid_date")),
        ({"expiry_date": "2026-10-29"}, (422, "items.0.expiry_date", "expiry_in_past")),  # 오늘(10-30)보다 과거
        ({"expiry_date": "2026-10-27"}, (422, "items.0.expiry_date", "expiry_in_past")),
        ({"expiry_in_days": -1}, (422, "items.0.expiry_in_days", "invalid_expiry_in_days")),
        ({"expiry_in_days": "3"}, (422, "items.0.expiry_in_days", "invalid_expiry_in_days")),
        ({"expiry_in_days": 1}, (422, "items.0.expiry_date", "expiry_in_past")),  # 구매일 10-28 + 1 = 10-29
    ],
)
def test_manual_line_expiry_errors(client, me, pg, analysis, extra, expected):
    assert shape(post(client, analysis, [line(0, "수제 닭가슴살", **extra)])) == expected
    assert foods_of(pg, me) == []


def test_manual_expiry_before_purchase_is_rejected(client, me, analysis):
    response = post(client, analysis, [line(0, "수제 닭가슴살", purchase_date="2026-12-01", expiry_date="2026-11-20")])
    assert shape(response) == (422, "items.0.expiry_date", "purchase_after_expiry")


def test_unchanged_name_ignores_expiry_fields(client, me, analysis):
    [food] = post(client, analysis, [line(0, "닭가슴살", expiry_date="2020-01-01", expiry_in_days=99)]).json()["items"]
    assert food["expiry_date"] == "2026-10-31"  # 규칙표(AI) 값으로 계산한다. 보낸 기한은 무시 (5절 9번과 같다)


# ---- 줄 검사 ----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("over", "expected"),
    [
        ({"name": "  "}, (422, "items.0.name", "required")),
        ({"name": None}, (422, "items.0.name", "required")),
        ({"unit": ""}, (422, "items.0.unit", "required")),
        ({"unit": ...}, (422, "items.0.unit", "required")),
        ({"quantity": 0}, (422, "items.0.quantity", "invalid_quantity")),
        ({"quantity": -1}, (422, "items.0.quantity", "invalid_quantity")),
        ({"quantity": "2"}, (422, "items.0.quantity", "invalid_quantity")),
        ({"quantity": 1.234}, (422, "items.0.quantity", "invalid_quantity")),
        ({"quantity": 100000000}, (422, "items.0.quantity", "invalid_quantity")),
        ({"quantity": ...}, (422, "items.0.quantity", "invalid_quantity")),
        ({"purchase_date": "2026-02-30"}, (422, "items.0.purchase_date", "invalid_date")),
        ({"purchase_date": ...}, (422, "items.0.purchase_date", "invalid_date")),
        ({"storage": "shelf"}, (422, "items.0.storage", "invalid_storage")),
        ({"storage": ...}, (422, "items.0.storage", "invalid_storage")),
        ({"storage": "room"}, (422, "items.0.storage", "storage_not_allowed")),  # 닭가슴살은 상온 불가
    ],
)
def test_line_input_errors_name_the_line_and_the_field(client, me, pg, analysis, over, expected):
    assert shape(post(client, analysis, [line(0, **over)])) == expected
    assert foods_of(pg, me) == [] and count(pg, "photo_analyses") == 1


def test_error_message_uses_the_field_label_without_the_line_position(client, me, analysis):
    response = post(client, analysis, [line(0), line(2, "김치", unit="")])
    assert shape(response) == (422, "items.1.unit", "required")  # N 은 보낸 목록에서의 위치다 (5절 27번)
    assert response.json()["message"] == "단위 칸을 채워 주세요."


def test_only_the_first_error_is_returned_in_the_documented_order(client, me, analysis):
    # 한 줄 안: 이름 → 단위 → 수량 → 구매일 → 보관 방법
    bad = line(0, name=" ", unit="", quantity=0, purchase_date="x", storage="x")
    assert shape(post(client, analysis, [bad])) == (422, "items.0.name", "required")
    bad.update(name="닭가슴살")
    assert shape(post(client, analysis, [bad]))[1:] == ("items.0.unit", "required")
    bad.update(unit="팩")
    assert shape(post(client, analysis, [bad]))[1:] == ("items.0.quantity", "invalid_quantity")
    bad.update(quantity=1)
    assert shape(post(client, analysis, [bad]))[1:] == ("items.0.purchase_date", "invalid_date")
    bad.update(purchase_date="2026-10-28")
    assert shape(post(client, analysis, [bad]))[1:] == ("items.0.storage", "invalid_storage")


def test_earlier_lines_are_reported_before_later_lines(client, me, analysis):
    response = post(client, analysis, [line(0, quantity=0), line(2, name=" ")])
    assert shape(response) == (422, "items.0.quantity", "invalid_quantity")


def test_item_number_is_checked_before_the_rest_of_the_line(client, me, analysis):
    assert shape(post(client, analysis, [line(9, name=" ")])) == (422, "items.0.item_no", "invalid_item")


@pytest.mark.parametrize("number", [3, 99, -1, "0", None, True, 1.0, [0]])
def test_unknown_item_number_is_invalid_item(client, me, analysis, number):
    response = post(client, analysis, [line(0), line(number, "김치")])
    assert shape(response) == (422, "items.1.item_no", "invalid_item")


def test_missing_item_number_and_non_object_lines_are_invalid_item(client, me, analysis):
    assert shape(post(client, analysis, [{"name": "닭가슴살"}])) == (422, "items.0.item_no", "invalid_item")
    assert shape(post(client, analysis, ["닭가슴살"])) == (422, "items.0.item_no", "invalid_item")


def test_the_same_item_number_twice_is_invalid_item(client, me, pg, analysis):
    response = post(client, analysis, [line(0), line(0, "닭가슴살", quantity=5)])
    assert shape(response) == (422, "items.1.item_no", "invalid_item")
    assert foods_of(pg, me) == []


# ---- 전부 성공하거나 전부 취소 --------------------------------------------------------------------------
def test_one_bad_line_cancels_everything_and_keeps_the_analysis(client, me, pg_rules, pg, analysis):
    before_rules = len(rules_repo.list_rules(pg_rules))
    response = post(client, analysis, [line(0, "닭가슴살"), line(2, "김치", quantity=0)])
    assert response.status_code == 422
    assert foods_of(pg, me) == []  # 앞 줄도 등록되지 않았다 (D-110)
    assert len(rules_repo.list_rules(pg)) == before_rules and rules_repo.get_rule_by_name(pg, "닭가슴살") is None
    assert photo_analyses_repo.get_valid_analysis(pg, me, analysis) is not None  # 읽기 결과는 남아 다시 시도할 수 있다
    assert post(client, analysis, [line(0, "닭가슴살"), line(2, "김치")]).status_code == 201  # 고쳐서 다시


def test_a_failure_while_saving_cancels_everything(client, me, pg, analysis, monkeypatch):
    real, calls = foods_repo.create_food, []

    def flaky(*args, **kwargs):
        calls.append(kwargs["name"])
        if len(calls) == 2:
            raise RuntimeError("DB 가 중간에 끊겼다")
        return real(*args, **kwargs)

    monkeypatch.setattr(foods_repo, "create_food", flaky)
    response = post(client, analysis, [line(0, "닭가슴살"), line(2, "김치")])
    assert shape(response) == (500, None, "server_error")
    assert foods_of(pg, me) == []
    assert rules_repo.get_rule_by_name(pg, "닭가슴살") is None and rules_repo.get_rule_by_name(pg, "김치") is None  # 규칙표에도 더해지지 않았다 (D-136)
    assert photo_analyses_repo.get_valid_analysis(pg, me, analysis) is not None


def test_the_analysis_removal_is_part_of_the_same_bundle(client, me, pg, analysis, monkeypatch):
    monkeypatch.setattr(photo_analyses_repo, "delete_analysis", lambda *a, **k: False)  # 다른 요청이 먼저 썼다
    assert shape(post(client, analysis, [line(0)])) == (422, None, "analysis_expired")
    assert foods_of(pg, me) == [] and rules_repo.get_rule_by_name(pg, "닭가슴살") is None


def test_nothing_outside_the_request_is_changed(client, me, pg_rules, pg, analysis):
    pg.execute("INSERT INTO users (email, password_hash) VALUES ('keep@example.com', 'x')")
    pg.commit()
    before = {t: count(pg, t) for t in ("users", "sessions", "rule_aliases")}
    post(client, analysis, [line(0)])
    assert {t: count(pg, t) for t in before} == before


# ---- 사진 읽기(F1)에서 한꺼번에 등록(F2)까지 -----------------------------------------------------------
def test_photo_analysis_then_bulk_registration_end_to_end(client, me, pg_rules, pg, monkeypatch):
    from app import ai

    monkeypatch.setattr(ai, "read_photo", lambda image, media_type: {
        "items": [
            {"name": "닭가슴살", "recommended_storage": "fridge", "storages": storages(fridge=3, freezer=90)},
            {"name": "계란", "recommended_storage": "freezer", "storages": storages(room=1, fridge=1, freezer=1)},  # 별칭: 규칙표 값으로 바뀐다
            {"name": "두리안", "recommended_storage": "room", "storages": storages(room=0, fridge=5)},  # 규칙 위반: 빠진다
        ],
        "receipt_date": "2026-10-29",
    })
    read = client.post("/photos/analyze", files={"image": ("r.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png")}).json()
    assert [(i["item_no"], i["name"], i["from_rule"]) for i in read["items"]] == [(0, "닭가슴살", False), (1, "달걀", True)]

    items = [
        {"item_no": i["item_no"], "name": i["name"], "quantity": 2, "unit": "개",
         "purchase_date": i["purchase_date"], "storage": i["recommended_storage"]}
        for i in read["items"]
    ]
    response = client.post("/foods/bulk", json={"analysis_id": read["analysis_id"], "items": items})
    assert response.status_code == 201
    assert [(f["name"], f["source"], f["purchase_date"]) for f in response.json()["items"]] == [
        ("닭가슴살", "rule", "2026-10-29"), ("달걀", "rule", "2026-10-29")]
    assert rules_repo.get_rule_by_name(pg, "닭가슴살") is not None  # 등록을 확정해서 규칙표에 더해졌다
    assert [f["name"] for f in client.get("/foods").json()["items"]] == ["닭가슴살", "달걀"]  # 홈에 나온다
    assert count(pg, "photo_analyses") == 0
