"""기록 (API-SPEC D1 숫자 · D2 처리한 식품 목록). 오늘은 2026-10-30 이다."""
import psycopg
import pytest

from app.db import records_repo

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


def add(client, name="수제청", storage="room", expiry="2026-12-01", purchase="2026-10-30", **over):
    body = dict(name=name, quantity=1, unit="개", purchase_date=purchase, storage=storage, expiry_date=expiry)
    body.update(over)
    response = client.post("/foods/manual", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def process(client, food, status, on=None, pg=None):
    """처리한다. on 을 주면 처리한 날짜를 그 날로 바꾼다 (시험에서 과거에 처리한 것처럼 만들려고)."""
    assert client.patch(f"/foods/{food['id']}/process", json={"status": status}).status_code == 200
    if on:
        pg.execute("UPDATE foods SET processed_date = %s WHERE id = %s", (on, food["id"]))
        pg.commit()


def insert_raw(pg, name, purchase, expiry, storage="room", email="kim@example.com"):
    """과거 기한 식품은 등록으로 만들 수 없어서 표에 바로 넣는다."""
    pg.execute(
        "INSERT INTO foods (user_id, name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " SELECT id, %s, %s, 1, '개', %s, %s, 'manual' FROM users WHERE email = %s",
        (name, storage, purchase, expiry, email),
    )
    pg.commit()


ZERO = {
    "eaten": {"year": 0, "month": 0},
    "discarded": {"year": 0, "month": 0},
    "food_kinds": 0,
    "by_storage": {"room": 0, "fridge": 0, "freezer": 0},
    "by_status": {"fresh": 0, "warning": 0, "soon": 0, "expired": 0},
}

# ---- 로그인이 필요하다 ----------------------------------------------------------------------------
@pytest.mark.parametrize("path", ["/records/summary", "/records/foods"])
def test_records_need_login(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json() == {"field": None, "reason": "login_required", "message": "다시 로그인해 주세요."}


@pytest.mark.parametrize("path", ["/records/summary", "/records/foods"])
def test_records_reject_after_30_minutes(me, pg, path):
    pg.execute("UPDATE sessions SET last_used_at = now() - interval '31 minutes'")
    pg.commit()
    assert shape(me.get(path)) == (401, None, "login_required")


# ---- D1 기록 숫자 ---------------------------------------------------------------------------------
def test_d1_all_zero_when_nothing_exists_is_not_an_error(me):
    response = me.get("/records/summary")
    assert response.status_code == 200 and response.json() == ZERO


def test_d1_has_exactly_the_spec_shape(me):
    body = me.get("/records/summary").json()
    assert list(body) == ["eaten", "discarded", "food_kinds", "by_storage", "by_status"]
    assert set(body["eaten"]) == {"year", "month"} == set(body["discarded"])
    assert set(body["by_storage"]) == {"room", "fridge", "freezer"}
    assert set(body["by_status"]) == {"fresh", "warning", "soon", "expired"}


def test_d1_eaten_and_discarded_by_year_and_month(me, pg):
    process(me, add(me, name="a"), "eaten")  # 오늘 처리
    process(me, add(me, name="b"), "eaten", "2026-10-01", pg)  # 이번 달
    process(me, add(me, name="c"), "eaten", "2026-01-01", pg)  # 올해, 다른 달
    process(me, add(me, name="d"), "eaten", "2025-12-31", pg)  # 작년
    process(me, add(me, name="e"), "discarded")
    process(me, add(me, name="f"), "discarded", "2026-09-30", pg)
    process(me, add(me, name="g"), "discarded", "2025-10-15", pg)  # 작년 같은 달
    body = me.get("/records/summary").json()
    assert body["eaten"] == {"year": 3, "month": 2}
    assert body["discarded"] == {"year": 2, "month": 1}
    # 처리한 식품은 현재 식품이 아니다
    assert (body["food_kinds"], body["by_storage"], body["by_status"]) == (0, ZERO["by_storage"], ZERO["by_status"])


def test_d1_food_kinds_count_same_name_once_and_exact_names_only(me):
    add(me, name="우유직접")
    add(me, name="우유직접")
    add(me, name="두부직접")
    add(me, name="두부직접 ")  # 앞뒤 공백은 저장할 때 지워지므로 같은 이름이다
    add(me, name="Milk")
    add(me, name="milk")  # 글자가 완전히 같을 때만 한 종류
    assert me.get("/records/summary").json()["food_kinds"] == 4


def test_d1_by_storage_counts_current_foods_only(me):
    add(me, name="a", storage="room")
    add(me, name="b", storage="fridge")
    add(me, name="c", storage="fridge")
    process(me, add(me, name="d", storage="freezer"), "eaten")
    assert me.get("/records/summary").json()["by_storage"] == {"room": 1, "fridge": 2, "freezer": 0}


def test_d1_by_status_uses_the_same_judgement_as_home_and_counts_long_expired(me, pg):
    for name, expiry in [("f6", "2026-11-05"), ("w5", "2026-11-04"), ("w3", "2026-11-02"), ("s2", "2026-11-01"), ("s0", "2026-10-30")]:
        add(me, name=name, expiry=expiry)
    insert_raw(pg, "e1", "2026-10-01", "2026-10-29")  # 하루 지남
    insert_raw(pg, "e4", "2026-10-01", "2026-10-26")  # 지난 지 4일 (달력에서만 빠진다)
    insert_raw(pg, "e40", "2026-09-01", "2026-09-20")  # 한참 지남
    summary = me.get("/records/summary").json()
    assert summary["by_status"] == {"fresh": 1, "warning": 2, "soon": 2, "expired": 3}
    # 홈 목록의 판정과 같다 (4일 이상 지난 것도 목록에서는 지남이다)
    home = me.get("/foods").json()["items"]
    for key in ("fresh", "warning", "soon", "expired"):
        assert summary["by_status"][key] == len([f for f in home if f["expiry_status"] == key])
    assert sum(summary["by_status"].values()) == len(home) == sum(summary["by_storage"].values())


def test_d1_counts_only_my_foods(me, other):
    process(me, add(me, name="내것"), "eaten")
    add(other, name="남의것")
    process(other, add(other, name="남의것2"), "discarded")
    mine = me.get("/records/summary").json()
    assert mine["eaten"]["year"] == 1 and mine["discarded"]["year"] == 0 and mine["food_kinds"] == 0
    theirs = other.get("/records/summary").json()
    assert theirs["eaten"]["year"] == 0 and theirs["discarded"]["year"] == 1 and theirs["food_kinds"] == 1


def test_d1_deleted_food_is_not_counted_but_discarded_is(me):
    gone = add(me, name="지움")
    assert me.delete(f"/foods/{gone['id']}").status_code == 204
    process(me, add(me, name="버림"), "discarded")
    assert me.get("/records/summary").json() == {**ZERO, "discarded": {"year": 1, "month": 1}}


def test_d1_restore_moves_a_food_from_the_counts_back_to_current(me):
    food = add(me, name="되돌림", storage="fridge")
    process(me, food, "eaten")
    assert me.get("/records/summary").json()["eaten"] == {"year": 1, "month": 1}
    assert me.patch(f"/foods/{food['id']}/restore").status_code == 200
    body = me.get("/records/summary").json()
    assert body["eaten"] == {"year": 0, "month": 0}
    assert (body["food_kinds"], body["by_storage"]["fridge"], body["by_status"]["fresh"]) == (1, 1, 1)


def test_d1_restored_expired_food_counts_as_expired(me, pg):
    food = add(me, name="지난식품", expiry="2026-10-31")
    process(me, food, "eaten")
    pg.execute("UPDATE foods SET purchase_date = '2026-10-01', expiry_date = '2026-10-20' WHERE id = %s", (food["id"],))
    pg.commit()
    me.patch(f"/foods/{food['id']}/restore")
    assert me.get("/records/summary").json()["by_status"]["expired"] == 1


def test_d1_db_failure_is_server_error(me, monkeypatch):
    def boom(*args, **kwargs):
        raise psycopg.OperationalError("db is down")

    monkeypatch.setattr(records_repo, "records_summary", boom)
    response = me.get("/records/summary")
    assert shape(response) == (500, None, "server_error")
    assert response.json()["message"] == "처리하지 못했어요. 잠시 뒤에 다시 해 주세요."


# ---- D2 처리한 식품 목록 -------------------------------------------------------------------------
def test_d2_empty_lists_when_nothing_processed(me):
    add(me)  # 처리 안 한 식품은 나오지 않는다
    response = me.get("/records/foods")
    assert response.status_code == 200 and response.json() == {"eaten": [], "discarded": []}


def test_d2_split_and_ordered_latest_first_then_by_name(me, pg):
    for name, status, on in [
        ("가", "eaten", "2026-10-28"), ("나", "eaten", "2026-10-30"), ("다", "eaten", "2026-10-30"),
        ("라", "discarded", "2026-10-01"), ("마", "discarded", "2026-10-29"),
    ]:
        process(me, add(me, name=name), status, on, pg)
    body = me.get("/records/foods").json()
    assert [f["name"] for f in body["eaten"]] == ["나", "다", "가"]  # 최근 처리한 순, 같은 날은 이름순
    assert [f["name"] for f in body["discarded"]] == ["마", "라"]


def test_d2_each_line_has_exactly_the_spec_fields(me):
    food = add(me, name="우유직접", quantity=1.5, unit="L")
    process(me, food, "eaten")
    line = me.get("/records/foods").json()["eaten"][0]
    assert line == {"id": food["id"], "name": "우유직접", "quantity": 1.5, "unit": "L", "processed_date": "2026-10-30"}


def test_d2_only_my_processed_foods(me, other):
    process(me, add(me, name="내것"), "eaten")
    process(other, add(other, name="남의것"), "discarded")
    mine, theirs = me.get("/records/foods").json(), other.get("/records/foods").json()
    assert [f["name"] for f in mine["eaten"]] == ["내것"] and mine["discarded"] == []
    assert [f["name"] for f in theirs["discarded"]] == ["남의것"] and theirs["eaten"] == []


def test_d2_pick_a_line_and_restore_it(me, other):
    food = add(me, name="되돌릴것")
    process(me, food, "discarded")
    line = me.get("/records/foods").json()["discarded"][0]
    assert other.patch(f"/foods/{line['id']}/restore").status_code == 404  # 남은 되돌릴 수 없다
    assert me.get("/records/foods").json()["discarded"] != []
    assert me.patch(f"/foods/{line['id']}/restore").status_code == 200
    assert me.get("/records/foods").json() == {"eaten": [], "discarded": []}
    assert [f["id"] for f in me.get("/foods").json()["items"]] == [food["id"]]


def test_d2_deleted_foods_never_appear(me):
    food = add(me, name="지움")
    me.delete(f"/foods/{food['id']}")
    process(me, add(me, name="버림"), "discarded")
    body = me.get("/records/foods").json()
    assert body["eaten"] == [] and [f["name"] for f in body["discarded"]] == ["버림"]


def test_d2_db_failure_is_server_error(me, monkeypatch):
    from app.db import foods_repo

    def boom(*args, **kwargs):
        raise psycopg.OperationalError("db is down")

    monkeypatch.setattr(foods_repo, "list_processed_foods", boom)
    assert shape(me.get("/records/foods")) == (500, None, "server_error")
