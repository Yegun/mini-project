from datetime import date
from decimal import Decimal

from app import foods_store


def add_food(conn, **overrides):
    values = {
        "name": "두부",
        "storage": "fridge",
        "quantity": Decimal("1"),
        "unit": "모",
        "purchase_date": date(2026, 10, 20),
        "expiry_date": date(2026, 11, 5),
        "source": "rule",
    }
    values.update(overrides)
    food = foods_store.create_food(conn, **values)
    conn.commit()
    return food


def error_body(response):
    """오류는 항상 칸 이름 + 이유 + 쉬운 문구 세 칸이다."""
    body = response.json()
    assert set(body) == {"field", "reason", "message"}
    assert isinstance(body["message"], str) and body["message"] != ""
    return body["field"], body["reason"]


# ---- A1 홈 목록 GET /foods ----
def test_a1_empty_home(client):
    response = client.get("/foods")
    assert response.status_code == 200
    assert response.json() == {"today": "2026-10-30", "foods": []}


def test_a1_adds_status_days_left_and_calendar_flag(client, conn):
    add_food(conn, name="여유", expiry_date=date(2026, 11, 5))  # 남은 날 6
    add_food(conn, name="주의", expiry_date=date(2026, 11, 2))  # 3
    add_food(conn, name="임박", expiry_date=date(2026, 11, 1))  # 2
    add_food(conn, name="지남", expiry_date=date(2026, 10, 28))  # -2
    add_food(conn, name="오래지남", expiry_date=date(2026, 10, 26))  # -4

    foods = {f["name"]: f for f in client.get("/foods").json()["foods"]}
    assert (foods["여유"]["expiry_status"], foods["여유"]["days_left"]) == ("fresh", 6)
    assert (foods["주의"]["expiry_status"], foods["주의"]["days_left"]) == ("warning", 3)
    assert (foods["임박"]["expiry_status"], foods["임박"]["days_left"]) == ("soon", 2)
    assert (foods["지남"]["expiry_status"], foods["지남"]["days_left"]) == ("expired", -2)
    assert foods["지남"]["show_on_calendar"] is True
    assert foods["오래지남"]["show_on_calendar"] is False  # 목록에는 남고 달력에서만 빠진다
    assert foods["여유"]["show_on_calendar"] is True


def test_a1_food_has_the_db_fields_with_text_dates(client, conn):
    add_food(conn)
    food = client.get("/foods").json()["foods"][0]
    assert set(food) == {
        "id", "name", "storage", "quantity", "unit", "purchase_date",
        "expiry_date", "source", "status",
        "expiry_status", "days_left", "show_on_calendar",
    }  # fmt: skip
    assert food["purchase_date"] == "2026-10-20"
    assert food["expiry_date"] == "2026-11-05"
    assert food["status"] == "none"
    assert food["source"] == "rule"
    assert food["quantity"] == 1.0


def test_a1_sorted_by_expiry_then_purchase_then_name(client, conn):
    add_food(conn, name="나", purchase_date=date(2026, 10, 10), expiry_date=date(2026, 11, 5))
    add_food(conn, name="가", purchase_date=date(2026, 10, 10), expiry_date=date(2026, 11, 5))
    add_food(conn, name="다", purchase_date=date(2026, 10, 1), expiry_date=date(2026, 11, 5))
    add_food(conn, name="라", purchase_date=date(2026, 10, 30), expiry_date=date(2026, 11, 1))
    names = [f["name"] for f in client.get("/foods").json()["foods"]]
    assert names == ["라", "다", "가", "나"]


def test_a1_hides_processed_foods(client, conn):
    keep = add_food(conn, name="당근")
    eaten = add_food(conn, name="우유")
    foods_store.set_status(conn, eaten["id"], "eaten")
    conn.commit()
    names = [f["name"] for f in client.get("/foods").json()["foods"]]
    assert names == [keep["name"]]


# ---- A5 상세 GET /foods/{id} ----
def test_a5_returns_the_food(client, conn):
    food = add_food(conn)
    response = client.get(f"/foods/{food['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == food["id"]
    assert body["expiry_status"] == "fresh"
    assert body["days_left"] == 6


def test_a5_missing_food_is_404(client):
    response = client.get("/foods/없는-번호")
    assert response.status_code == 404
    assert error_body(response) == (None, "not_found")


def test_a5_processed_food_is_404_like_a_missing_one(client, conn):
    food = add_food(conn)
    foods_store.set_status(conn, food["id"], "discarded")
    conn.commit()
    response = client.get(f"/foods/{food['id']}")
    assert response.status_code == 404  # 처리된 식품은 없는 식품과 똑같이 (D-037)
    assert error_body(response) == (None, "not_found")


# ---- A8 다 먹음 / 버림 PATCH /foods/{id}/process ----
def test_a8_eaten_keeps_row_and_leaves_home(client, conn):
    food = add_food(conn)
    response = client.patch(f"/foods/{food['id']}/process", json={"status": "eaten"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "eaten"
    assert body["expiry_status"] is None
    assert body["days_left"] is None
    assert body["show_on_calendar"] is None
    assert client.get("/foods").json()["foods"] == []
    assert foods_store.get_food(conn, food["id"], include_processed=True)["status"] == "eaten"  # 행은 남는다


def test_a8_discarded(client, conn):
    food = add_food(conn)
    response = client.patch(f"/foods/{food['id']}/process", json={"status": "discarded"})
    assert response.status_code == 200
    assert response.json()["status"] == "discarded"


def test_a8_cannot_go_back_or_use_other_values(client, conn):
    food = add_food(conn)
    for value in ("none", "아무거나", None, 1):
        response = client.patch(f"/foods/{food['id']}/process", json={"status": value})
        assert response.status_code == 422
        assert error_body(response)[0] == "status"
    assert foods_store.get_food(conn, food["id"])["status"] == "none"


def test_a8_already_processed_is_404_like_a_missing_one(client, conn):
    food = add_food(conn)
    client.patch(f"/foods/{food['id']}/process", json={"status": "eaten"})
    response = client.patch(f"/foods/{food['id']}/process", json={"status": "discarded"})
    assert response.status_code == 404  # 처리된 식품은 없는 식품과 똑같이 (D-037)
    assert error_body(response) == (None, "not_found")


def test_a8_missing_food_is_404(client):
    response = client.patch("/foods/없는-번호/process", json={"status": "eaten"})
    assert response.status_code == 404
    assert error_body(response) == (None, "not_found")


def test_a8_bad_body_uses_the_same_error_shape(client, conn):
    food = add_food(conn)
    response = client.patch(f"/foods/{food['id']}/process", json={"status": "eaten", "x": 1})
    assert response.status_code == 422
    assert error_body(response) == ("x", "invalid")
    response = client.patch(
        f"/foods/{food['id']}/process",
        content="이건 JSON 이 아님",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert error_body(response)[1] == "invalid"


# ---- A9 삭제 DELETE /foods/{id} ----
def test_a9_deletes_the_row_completely(client, conn):
    food = add_food(conn)
    response = client.delete(f"/foods/{food['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert foods_store.get_food(conn, food["id"]) is None
    assert client.get(f"/foods/{food['id']}").status_code == 404


def test_a9_missing_food_is_404(client):
    response = client.delete("/foods/없는-번호")
    assert response.status_code == 404
    assert error_body(response) == (None, "not_found")


def test_a9_processed_food_is_404_like_a_missing_one(client, conn):
    food = add_food(conn)
    foods_store.set_status(conn, food["id"], "eaten")
    conn.commit()
    response = client.delete(f"/foods/{food['id']}")
    assert response.status_code == 404  # 처리된 식품은 없는 식품과 똑같이 (D-037)
    assert error_body(response) == (None, "not_found")
    assert foods_store.get_food(conn, food["id"], include_processed=True) is not None  # 행은 그대로


# ---- 서버가 저장소를 못 열 때 ----
def test_failed_storage_returns_the_same_error_shape(client, conn):
    conn.close()  # 창고가 닫힌 상황을 흉내 낸다
    response = client.get("/foods")
    assert response.status_code == 500
    assert error_body(response) == (None, "load_failed")
