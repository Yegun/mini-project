"""식품 창구 (API-SPEC A1 ~ A4, A7, A8, D3)와 규칙표 검색(C1). 로그인한 계정의 식품만 다루는지, 확인 순서, 응답 모양을 본다."""
import psycopg
import pytest

from app.db import foods_repo

PW = "Passw0rd!"


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


def rule_food(**over):
    data = dict(name="양파", quantity=2, unit="개", purchase_date="2026-10-30", storage="room")
    data.update(over)
    return data


def manual_food(**over):
    data = dict(name="수제청", quantity=1, unit="병", purchase_date="2026-10-30", storage="room", expiry_date="2026-12-01")
    data.update(over)
    return data


def add_rule(client, **over):
    response = client.post("/foods", json=rule_food(**over))
    assert response.status_code == 201, response.text
    return response.json()


def add_manual(client, **over):
    response = client.post("/foods/manual", json=manual_food(**over))
    assert response.status_code == 201, response.text
    return response.json()


def count(pg, table="foods"):
    return pg.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


FOOD_KEYS = {
    "id", "name", "storage", "quantity", "unit", "purchase_date", "expiry_date", "source", "status",
    "processed_date", "expiry_status", "days_left", "show_on_calendar",
}

# ---- 로그인이 필요하다 (모든 🔒 창구) ---------------------------------------------------------------
FAKE = "0b0e0b8e-3f4b-4f43-9f0a-5d5b0d9b3b11"
PROTECTED = [
    ("get", "/rules?q=양"), ("get", "/foods"), ("post", "/foods"), ("post", "/foods/manual"),
    ("get", f"/foods/{FAKE}"), ("patch", f"/foods/{FAKE}/process"), ("patch", f"/foods/{FAKE}/restore"),
    ("delete", f"/foods/{FAKE}"),
]


@pytest.mark.parametrize("method, path", PROTECTED)
def test_every_protected_route_needs_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert response.json() == {"field": None, "reason": "login_required", "message": "다시 로그인해 주세요."}


@pytest.mark.parametrize("method, path", PROTECTED)
def test_expired_login_is_rejected_everywhere(me, pg, method, path):
    pg.execute("UPDATE sessions SET last_used_at = now() - interval '31 minutes'")
    pg.commit()
    assert shape(getattr(me, method)(path)) == (401, None, "login_required")


# ---- C1 규칙표 검색 ---------------------------------------------------------------------------
def test_search_by_name_part_gives_name_default_and_disallowed(me):
    response = me.get("/rules", params={"q": "양"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert [i["name"] for i in items] == ["양배추", "양파"]  # 이름순
    assert set(items[0]) == {"name", "default_storage", "disallowed_storages"}
    onion = next(i for i in items if i["name"] == "양파")
    assert (onion["default_storage"], onion["disallowed_storages"]) == ("room", [])


def test_search_shows_disallowed_in_storage_order(me):
    milk = me.get("/rules", params={"q": "우유"}).json()["items"][0]
    assert milk == {"name": "우유", "default_storage": "fridge", "disallowed_storages": ["room", "freezer"]}


def test_search_by_alias_shows_the_food_name_once(me):
    assert [i["name"] for i in me.get("/rules", params={"q": "계란"}).json()["items"]] == ["달걀"]
    assert [i["name"] for i in me.get("/rules", params={"q": "고기"}).json()["items"]] == ["닭고기", "돼지고기", "소고기"]


def test_search_empty_or_nothing_found_is_an_empty_list(me):
    for params in ({}, {"q": ""}, {"q": "   "}, {"q": "없는식품"}, {"q": "%"}):
        response = me.get("/rules", params=params)
        assert (response.status_code, response.json()) == (200, {"items": []})


def test_search_does_not_show_foods_registered_by_hand(me, other):
    add_manual(me, name="수제청")
    assert other.get("/rules", params={"q": "수제"}).json() == {"items": []}
    assert me.get("/rules", params={"q": "수제"}).json() == {"items": []}


# ---- A2 규칙표 식품 등록 ----------------------------------------------------------------------
def test_a2_creates_with_expiry_from_the_rule(me, pg):
    response = me.post("/foods", json=rule_food())
    assert response.status_code == 201
    food = response.json()
    assert set(food) == FOOD_KEYS
    assert (food["name"], food["storage"], food["quantity"], food["unit"]) == ("양파", "room", 2, "개")
    assert (food["purchase_date"], food["expiry_date"]) == ("2026-10-30", "2026-11-29")  # 상온 30일
    assert (food["source"], food["status"], food["processed_date"]) == ("rule", "none", None)
    assert (food["expiry_status"], food["days_left"], food["show_on_calendar"]) == ("fresh", 30, True)
    assert len(food["id"]) == 36 and count(pg) == 1


def test_a2_expiry_follows_the_chosen_storage(me):
    assert add_rule(me, storage="fridge")["expiry_date"] == "2026-12-29"  # 냉장 60일
    assert add_rule(me, storage="freezer")["expiry_date"] == "2027-04-28"  # 냉동 180일


def test_a2_alias_is_saved_with_the_official_name(me):
    food = add_rule(me, name="계란", storage="fridge")
    assert food["name"] == "달걀"
    assert me.get("/foods").json()["items"][0]["name"] == "달걀"


def test_a2_trims_name_and_unit_and_allows_future_date_and_decimals(me):
    food = add_rule(me, name=" 양파 ", unit=" 개 ", quantity=0.25, purchase_date="2027-01-05")
    assert (food["name"], food["unit"], food["quantity"]) == ("양파", "개", 0.25)
    assert food["expiry_date"] == "2027-02-04"
    assert food["days_left"] == 97  # 2026-10-30 → 2027-02-04


def test_a2_same_food_can_be_registered_again(me):
    first, second = add_rule(me), add_rule(me)
    assert first["id"] != second["id"]
    assert len(me.get("/foods").json()["items"]) == 2


@pytest.mark.parametrize(
    "over, expected",
    [
        ({"name": ""}, (422, "name", "required")),
        ({"name": None}, (422, "name", "required")),
        ({"unit": "  "}, (422, "unit", "required")),
        ({"quantity": None}, (422, "quantity", "invalid_quantity")),
        ({"quantity": 0}, (422, "quantity", "invalid_quantity")),
        ({"quantity": -1}, (422, "quantity", "invalid_quantity")),
        ({"quantity": 1.234}, (422, "quantity", "invalid_quantity")),
        ({"quantity": 100000000}, (422, "quantity", "invalid_quantity")),
        ({"quantity": "2"}, (422, "quantity", "invalid_quantity")),
        ({"purchase_date": "2026-02-30"}, (422, "purchase_date", "invalid_date")),
        ({"purchase_date": None}, (422, "purchase_date", "invalid_date")),
        ({"storage": "shelf"}, (422, "storage", "invalid_storage")),
        ({"storage": None}, (422, "storage", "invalid_storage")),
        ({"name": "없는식품"}, (422, "name", "rule_not_found")),
        ({"name": "우유", "storage": "room"}, (422, "storage", "storage_not_allowed")),
        ({"name": "감자", "storage": "freezer"}, (422, "storage", "storage_not_allowed")),
    ],
)
def test_a2_errors_save_nothing(me, pg, over, expected):
    response = me.post("/foods", json=rule_food(**over))
    assert shape(response) == expected
    assert set(response.json()) == {"field", "reason", "message"}
    assert count(pg) == 0


def test_a2_checks_in_the_order_of_the_spec_table(me):
    # 이름·단위 → 수량 → 구매일 → 보관 방법 → 규칙표 이름 → 불가 보관 방법
    bad = dict(name="", unit="", quantity=0, purchase_date="x", storage="x")
    assert shape(me.post("/foods", json=bad))[1:] == ("name", "required")
    assert shape(me.post("/foods", json={**bad, "name": "양파"}))[1:] == ("unit", "required")
    assert shape(me.post("/foods", json={**bad, "name": "양파", "unit": "개"}))[1:] == ("quantity", "invalid_quantity")
    bad.update(name="양파", unit="개", quantity=1)
    assert shape(me.post("/foods", json=bad))[1:] == ("purchase_date", "invalid_date")
    bad["purchase_date"] = "2026-10-30"
    assert shape(me.post("/foods", json=bad))[1:] == ("storage", "invalid_storage")
    bad.update(storage="room", name="없는식품")
    assert shape(me.post("/foods", json=bad))[1:] == ("name", "rule_not_found")


def test_a2_ignores_unknown_fields_and_rejects_a_non_object_body(me):
    assert me.post("/foods", json={**rule_food(), "owner": "x"}).status_code == 201
    response = me.post("/foods", json=[1, 2])
    assert response.status_code == 422 and set(response.json()) == {"field", "reason", "message"}


# ---- A3 직접 등록 -----------------------------------------------------------------------------
def test_a3_creates_with_the_given_expiry_date(me, pg):
    response = me.post("/foods/manual", json=manual_food())
    assert response.status_code == 201
    food = response.json()
    assert set(food) == FOOD_KEYS
    assert (food["source"], food["status"], food["expiry_date"]) == ("manual", "none", "2026-12-01")
    assert (food["expiry_status"], food["days_left"]) == ("fresh", 32)
    assert count(pg, "rules") == 30  # 규칙표에는 더하지 않는다 (D-092)


def test_a3_days_later_is_purchase_date_plus_n(me):
    assert add_manual(me, expiry_date=None, expiry_in_days=3)["expiry_date"] == "2026-11-02"
    assert add_manual(me, expiry_date=None, expiry_in_days=0)["expiry_date"] == "2026-10-30"  # 0일 = 구매한 날
    assert add_manual(me, expiry_date="", expiry_in_days=5)["expiry_date"] == "2026-11-04"  # 빈 글자는 안 보낸 것


def test_a3_all_three_storages_and_future_purchase(me):
    for storage in ("room", "fridge", "freezer"):
        assert add_manual(me, storage=storage)["storage"] == storage
    food = add_manual(me, purchase_date="2026-11-10", expiry_date="2026-11-20")
    assert (food["purchase_date"], food["days_left"]) == ("2026-11-10", 21)


@pytest.mark.parametrize(
    "over, expected",
    [
        ({"name": ""}, (422, "name", "required")),
        ({"unit": ""}, (422, "unit", "required")),
        ({"quantity": 0}, (422, "quantity", "invalid_quantity")),
        ({"purchase_date": "nope"}, (422, "purchase_date", "invalid_date")),
        ({"storage": "x"}, (422, "storage", "invalid_storage")),
        ({"expiry_date": "2026-02-30"}, (422, "expiry_date", "invalid_date")),
        ({"expiry_date": None}, (422, "expiry_date", "expiry_input_invalid")),  # 기한을 안 보냄
        ({"expiry_in_days": 3}, (422, "expiry_date", "expiry_input_invalid")),  # 두 가지를 모두 보냄
        ({"expiry_date": "2026-10-29"}, (422, "expiry_date", "expiry_in_past")),
        ({"purchase_date": "2026-11-10", "expiry_date": "2026-11-05"}, (422, "expiry_date", "purchase_after_expiry")),
        ({"expiry_date": None, "expiry_in_days": -1}, (422, "expiry_in_days", "invalid_expiry_in_days")),
        ({"expiry_date": None, "expiry_in_days": 2.5}, (422, "expiry_in_days", "invalid_expiry_in_days")),
        ({"expiry_date": None, "expiry_in_days": "3"}, (422, "expiry_in_days", "invalid_expiry_in_days")),
        ({"purchase_date": "2026-10-01", "expiry_date": None, "expiry_in_days": 5}, (422, "expiry_date", "expiry_in_past")),
        ({"name": "양파"}, (422, "name", "rule_name_exists")),
        ({"name": "계란"}, (422, "name", "rule_name_exists")),  # 별칭도 규칙표 이름이다
    ],
)
def test_a3_errors_save_nothing(me, pg, over, expected):
    assert shape(me.post("/foods/manual", json=manual_food(**over))) == expected
    assert count(pg) == 0


def test_a3_input_errors_come_before_rule_name_exists(me):
    assert shape(me.post("/foods/manual", json=manual_food(name="양파", expiry_date="2026-10-29")))[1:] == (
        "expiry_date", "expiry_in_past",
    )


# ---- A1 홈 목록 -------------------------------------------------------------------------------
def test_a1_empty_list(me):
    assert me.get("/foods").json() == {"today": "2026-10-30", "items": []}


def test_a1_sorted_by_expiry_then_purchase_then_name(me):
    add_manual(me, name="다", purchase_date="2026-10-01", expiry_date="2026-11-10")
    add_manual(me, name="나", purchase_date="2026-10-20", expiry_date="2026-11-10")
    add_manual(me, name="가", purchase_date="2026-10-20", expiry_date="2026-11-10")
    add_manual(me, name="라", purchase_date="2026-10-29", expiry_date="2026-11-01")
    body = me.get("/foods").json()
    assert body["today"] == "2026-10-30"
    assert [f["name"] for f in body["items"]] == ["라", "다", "가", "나"]
    assert all(set(f) == FOOD_KEYS for f in body["items"])


def test_a1_computed_fields_and_expired_foods_stay_in_the_list(me, pg):
    for name, expiry in [("a", "2026-10-30"), ("b", "2026-11-04"), ("c", "2026-11-05")]:
        add_manual(me, name=name, purchase_date="2026-10-30", expiry_date=expiry)
    for name, purchase, expiry in [("old1", "2026-10-01", "2026-10-29"), ("old4", "2026-10-01", "2026-10-26")]:
        pg.execute(  # 과거 기한은 등록으로 만들 수 없어서 시험에서는 표에 직접 넣는다
            "INSERT INTO foods (user_id, name, storage, quantity, unit, purchase_date, expiry_date, source)"
            " SELECT id, %s, 'room', 1, '개', %s, %s, 'manual' FROM users LIMIT 1",
            (name, purchase, expiry),
        )
    pg.commit()
    got = {f["name"]: (f["expiry_status"], f["days_left"], f["show_on_calendar"]) for f in me.get("/foods").json()["items"]}
    assert got == {
        "a": ("soon", 0, True), "b": ("warning", 5, True), "c": ("fresh", 6, True),
        "old1": ("expired", -1, True), "old4": ("expired", -4, False),  # 지난 지 4일 이상은 달력에서만 빠진다
    }


def test_a1_shows_only_my_foods_and_unprocessed_ones(me, other):
    mine = add_manual(me, name="내것")
    add_manual(other, name="남의것")
    done = add_manual(me, name="처리함")
    assert me.patch(f"/foods/{done['id']}/process", json={"status": "eaten"}).status_code == 200
    assert [f["name"] for f in me.get("/foods").json()["items"]] == ["내것"]
    assert [f["name"] for f in other.get("/foods").json()["items"]] == ["남의것"]
    assert mine["id"] in [f["id"] for f in me.get("/foods").json()["items"]]


# ---- A4 식품 상세 -----------------------------------------------------------------------------
def test_a4_shows_one_food(me):
    food = add_manual(me)
    response = me.get(f"/foods/{food['id']}")
    assert response.status_code == 200 and response.json() == food


def test_a4_every_kind_of_missing_food_gives_the_same_not_found(me, other):
    mine = add_manual(me)
    done = add_manual(me, name="처리함")
    me.patch(f"/foods/{done['id']}/process", json={"status": "discarded"})
    answers = {
        "없는 번호": me.get(f"/foods/{FAKE}"),
        "남의 식품": other.get(f"/foods/{mine['id']}"),
        "처리된 식품": me.get(f"/foods/{done['id']}"),
        "번호 모양이 아님": me.get("/foods/abc"),
    }
    assert {r.status_code for r in answers.values()} == {404}
    assert len({r.text for r in answers.values()}) == 1  # 남의 식품이 있는지 드러나지 않는다 (D-063)
    assert answers["없는 번호"].json() == {"field": None, "reason": "not_found", "message": "찾을 수 없는 식품이에요."}


# ---- A7 다 먹음 / 버림 ------------------------------------------------------------------------
def test_a7_marks_eaten_with_todays_date_and_hides_from_home(me):
    food = add_manual(me)
    response = me.patch(f"/foods/{food['id']}/process", json={"status": "eaten"})
    assert response.status_code == 200
    done = response.json()
    assert (done["status"], done["processed_date"]) == ("eaten", "2026-10-30")
    assert (done["expiry_status"], done["days_left"], done["show_on_calendar"]) == (None, None, None)
    assert {k: done[k] for k in ("name", "quantity", "unit", "expiry_date")} == {
        k: food[k] for k in ("name", "quantity", "unit", "expiry_date")
    }
    assert me.get("/foods").json()["items"] == []
    assert me.get(f"/foods/{food['id']}").status_code == 404


def test_a7_discarded(me):
    food = add_manual(me)
    done = me.patch(f"/foods/{food['id']}/process", json={"status": "discarded"}).json()
    assert (done["status"], done["processed_date"]) == ("discarded", "2026-10-30")


def test_a7_cannot_process_twice_or_change_eaten_to_discarded(me, pg):
    food = add_manual(me)
    me.patch(f"/foods/{food['id']}/process", json={"status": "eaten"})
    again = me.patch(f"/foods/{food['id']}/process", json={"status": "discarded"})
    assert shape(again) == (404, None, "not_found")
    assert pg.execute("SELECT status FROM foods").fetchone()["status"] == "eaten"


def test_a7_not_found_comes_before_input_check_and_other_account_is_not_found(me, other):
    food = add_manual(me)
    assert shape(me.patch(f"/foods/{FAKE}/process", json={"status": "nope"})) == (404, None, "not_found")
    assert shape(other.patch(f"/foods/{food['id']}/process", json={"status": "eaten"})) == (404, None, "not_found")
    assert me.get(f"/foods/{food['id']}").status_code == 200  # 남이 건드려도 그대로다


@pytest.mark.parametrize("value", ["none", "", None, "ate", 1])
def test_a7_invalid_status(me, pg, value):
    food = add_manual(me)
    assert shape(me.patch(f"/foods/{food['id']}/process", json={"status": value})) == (422, "status", "invalid_status")
    assert pg.execute("SELECT status FROM foods").fetchone()["status"] == "none"


# ---- D3 홈으로 되돌리기 -----------------------------------------------------------------------
def test_d3_restores_everything_but_status_and_date(me):
    food = add_manual(me)
    me.patch(f"/foods/{food['id']}/process", json={"status": "eaten"})
    response = me.patch(f"/foods/{food['id']}/restore")
    assert response.status_code == 200
    assert response.json() == food  # 처리하기 전과 똑같다 (계산 칸도 다시 붙는다)
    assert [f["id"] for f in me.get("/foods").json()["items"]] == [food["id"]]


def test_d3_restored_food_that_expired_is_expired_again(me, pg):
    food = add_manual(me, expiry_date="2026-10-31")
    me.patch(f"/foods/{food['id']}/process", json={"status": "discarded"})
    pg.execute("UPDATE foods SET purchase_date = '2026-10-01', expiry_date = '2026-10-20'")  # 시간이 흘러 기한이 지났다고 본다
    pg.commit()
    restored = me.patch(f"/foods/{food['id']}/restore").json()
    assert (restored["expiry_status"], restored["days_left"]) == ("expired", -10)
    assert restored["expiry_date"] == "2026-10-20"  # 기한을 다시 계산하지 않는다 (D-076)


def test_d3_not_found_cases(me, other):
    active = add_manual(me, name="처리 안 함")
    done = add_manual(me, name="처리함")
    me.patch(f"/foods/{done['id']}/process", json={"status": "eaten"})
    for response in (
        me.patch(f"/foods/{active['id']}/restore"),  # 처리되지 않은 식품
        me.patch(f"/foods/{FAKE}/restore"),
        me.patch("/foods/abc/restore"),
        other.patch(f"/foods/{done['id']}/restore"),  # 남의 식품
    ):
        assert shape(response) == (404, None, "not_found")
    assert me.get(f"/foods/{done['id']}").status_code == 404  # 남이 시도해도 처리된 채 그대로다


def test_d3_deleted_food_cannot_be_restored(me):
    food = add_manual(me)
    assert me.delete(f"/foods/{food['id']}").status_code == 204
    assert me.patch(f"/foods/{food['id']}/restore").status_code == 404


# ---- A8 삭제 ----------------------------------------------------------------------------------
def test_a8_deletes_the_row_for_good(me, pg):
    food = add_manual(me)
    response = me.delete(f"/foods/{food['id']}")
    assert response.status_code == 204 and response.content == b""
    assert count(pg) == 0
    assert me.get(f"/foods/{food['id']}").status_code == 404
    assert shape(me.delete(f"/foods/{food['id']}")) == (404, None, "not_found")


def test_a8_cannot_delete_processed_or_other_accounts_food(me, other, pg):
    mine = add_manual(me, name="내것")
    done = add_manual(me, name="처리함")
    me.patch(f"/foods/{done['id']}/process", json={"status": "eaten"})
    assert shape(me.delete(f"/foods/{done['id']}")) == (404, None, "not_found")  # 먼저 되돌린 뒤 지운다 (V-20)
    assert shape(other.delete(f"/foods/{mine['id']}")) == (404, None, "not_found")
    assert shape(me.delete("/foods/abc")) == (404, None, "not_found")
    assert count(pg) == 2
    assert me.patch(f"/foods/{done['id']}/restore").status_code == 200
    assert me.delete(f"/foods/{done['id']}").status_code == 204


# ---- 두 계정은 서로의 식품을 볼 수 없다 ---------------------------------------------------------
def test_two_accounts_are_fully_separated(me, other):
    mine = add_manual(me, name="내것")
    theirs = add_manual(other, name="남의것")
    assert [f["name"] for f in me.get("/foods").json()["items"]] == ["내것"]
    assert [f["name"] for f in other.get("/foods").json()["items"]] == ["남의것"]
    for client, foreign in ((me, theirs), (other, mine)):
        assert client.get(f"/foods/{foreign['id']}").status_code == 404
        assert client.patch(f"/foods/{foreign['id']}/process", json={"status": "eaten"}).status_code == 404
        assert client.delete(f"/foods/{foreign['id']}").status_code == 404


# ---- 저장하다 실패하면 아무것도 바뀌지 않는다 (OQ-04) ------------------------------------------------
def test_db_failure_is_server_error_and_changes_nothing(me, pg, monkeypatch):
    def boom(*args, **kwargs):
        raise psycopg.OperationalError("db is down")

    monkeypatch.setattr(foods_repo, "create_food", boom)
    response = me.post("/foods", json=rule_food())
    assert response.status_code == 500
    assert response.json() == {
        "field": None, "reason": "server_error", "message": "처리하지 못했어요. 잠시 뒤에 다시 해 주세요.",
    }
    assert count(pg) == 0


def test_db_rule_hit_is_server_error_not_input_error(me, pg, monkeypatch):
    """API 검사를 통과했는데 DB 규칙에 걸리면 사용자 입력 오류가 아니라 server_error 다 (DATA-MODEL 6-5)."""
    real = foods_repo.create_food
    monkeypatch.setattr(foods_repo, "create_food", lambda conn, user_id, **kw: real(conn, user_id, **{**kw, "quantity": 0}))
    assert shape(me.post("/foods", json=rule_food())) == (500, None, "server_error")
    assert count(pg) == 0
