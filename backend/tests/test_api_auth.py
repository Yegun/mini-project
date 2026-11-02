"""가입 · 로그인 · 로그아웃 (API-SPEC B1 ~ B3). PostgreSQL 임시 schema 에서 서버 코드를 그대로 지난다."""
import psycopg
import pytest

from app.db import legacy_migration
from app.db.sessions_repo import _hash
from app.db.users_repo import find_user_by_email

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}


def count(pg, table):
    return pg.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def real_users(pg):
    """이전용 계정(legacy@fridge.invalid)을 뺀 실제 가입자 수."""
    return pg.execute("SELECT count(*) AS n FROM users WHERE email <> 'legacy@fridge.invalid'").fetchone()["n"]


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


# ---- B1 가입 ----------------------------------------------------------------------------------
def test_signup_creates_account_and_login_cookie(client, pg):
    response = client.post("/auth/signup", json=CRED)
    assert response.status_code == 201
    assert response.json() == {"email": "kim@example.com"}
    assert real_users(pg) == 1 and count(pg, "sessions") == 1
    token = client.cookies.get("session")
    assert token and pg.execute("SELECT 1 FROM sessions WHERE id = %s", (_hash(token),)).fetchone()


def test_signup_cookie_attributes_follow_the_spec(client):
    header = client.post("/auth/signup", json=CRED).headers["set-cookie"].lower()
    assert header.startswith("session=")
    assert "httponly" in header and "samesite=lax" in header
    assert "max-age" not in header and "expires" not in header and "secure" not in header  # 문서에 없는 속성은 정하지 않았다


def test_signup_stores_lowercase_email_and_hash_only(client, pg):
    response = client.post("/auth/signup", json={"email": "  Kim@Example.COM ", "password": "Passw0rd!"})
    assert response.status_code == 201 and response.json() == {"email": "kim@example.com"}
    stored = find_user_by_email(pg, "kim@example.com")["password_hash"]
    assert "Passw0rd!" not in stored and stored.startswith("$argon2")


def test_signup_then_protected_request_works_without_login(client):
    client.post("/auth/signup", json=CRED)
    assert client.post("/auth/logout").status_code == 204  # 가입만으로 로그인된 상태다


@pytest.mark.parametrize(
    "body, expected",
    [
        ({"email": "kim", "password": "Passw0rd!"}, (422, "email", "invalid_email")),
        ({"email": "kim@example", "password": "Passw0rd!"}, (422, "email", "invalid_email")),
        ({"email": None, "password": "Passw0rd!"}, (422, "email", "invalid_email")),
        ({"password": "Passw0rd!"}, (422, "email", "invalid_email")),
        ({"email": "kim@example.com", "password": "short1!"}, (422, "password", "weak_password")),
        ({"email": "kim@example.com", "password": "Password!"}, (422, "password", "weak_password")),
        ({"email": "kim@example.com", "password": "Passw0rd한!"}, (422, "password", "weak_password")),
        ({"email": "kim@example.com"}, (422, "password", "weak_password")),
        # 이메일 오류가 비밀번호 오류보다 먼저다
        ({"email": "kim", "password": "x"}, (422, "email", "invalid_email")),
    ],
)
def test_signup_input_errors_save_nothing(client, pg, body, expected):
    response = client.post("/auth/signup", json=body)
    assert shape(response) == expected
    assert set(response.json()) == {"field", "reason", "message"}
    assert real_users(pg) == 0 and count(pg, "sessions") == 0
    assert "session" not in response.headers.get("set-cookie", "")


def test_signup_existing_email_is_409_in_any_case(client, pg):
    assert client.post("/auth/signup", json=CRED).status_code == 201
    other = client.post("/auth/signup", json={"email": "KIM@example.com", "password": "Other1234!"})
    assert shape(other) == (409, "email", "email_taken")
    assert other.json()["message"] == "이미 가입된 이메일이에요."
    assert real_users(pg) == 1 and count(pg, "sessions") == 1  # 두 번째 요청은 아무것도 바꾸지 않았다


# ---- B2 로그인 --------------------------------------------------------------------------------
def test_login_success_makes_a_new_device_session(client, make_client, pg):
    client.post("/auth/signup", json=CRED)
    phone = make_client()
    response = phone.post("/auth/login", json={"email": "KIM@example.com", "password": "Passw0rd!"})
    assert response.status_code == 200 and response.json() == {"email": "kim@example.com"}
    assert phone.cookies.get("session") and phone.cookies.get("session") != client.cookies.get("session")
    assert count(pg, "sessions") == 2  # 기기마다 한 줄 (D-054)
    assert client.post("/auth/logout").status_code == 204  # 다른 기기의 로그인 상태는 그대로였다


def test_login_failures_all_look_the_same(client, pg):
    client.post("/auth/signup", json=CRED)
    sessions_before = count(pg, "sessions")
    bad = [
        {"email": "kim@example.com", "password": "wrong"},
        {"email": "nobody@example.com", "password": "Passw0rd!"},
        {"email": "kim", "password": "x"},  # 모양·규칙 검사는 하지 않는다
        {"email": "", "password": ""},
        {"email": 5, "password": ["x"]},
        {"password": "Passw0rd!"},
        {},
    ]
    results = [client.post("/auth/login", json=body) for body in bad]
    assert {r.status_code for r in results} == {401}
    assert len({r.text for r in results}) == 1  # 어느 쪽이 틀렸는지, 가입된 이메일인지 알 수 없다
    assert results[0].json() == {
        "field": None, "reason": "login_failed", "message": "이메일 또는 비밀번호가 맞지 않아요.",
    }
    assert count(pg, "sessions") == sessions_before


def test_login_has_no_attempt_limit(client):
    client.post("/auth/signup", json=CRED)
    for _ in range(6):
        assert client.post("/auth/login", json={**CRED, "password": "wrong"}).status_code == 401
    assert client.post("/auth/login", json=CRED).status_code == 200  # 틀려도 횟수 제한은 없다 (D-049)


def test_login_clears_expired_sessions_of_that_account(client, make_client, pg):
    client.post("/auth/signup", json=CRED)
    pg.execute("UPDATE sessions SET last_used_at = now() - interval '31 minutes'")
    pg.commit()
    make_client().post("/auth/login", json=CRED)
    assert count(pg, "sessions") == 1


# ---- B3 로그아웃 ------------------------------------------------------------------------------
def test_logout_ends_only_this_device(client, make_client, pg):
    client.post("/auth/signup", json=CRED)
    laptop = make_client()
    laptop.post("/auth/login", json=CRED)

    response = client.post("/auth/logout")
    assert response.status_code == 204 and response.content == b""
    assert "session=" in response.headers["set-cookie"]  # 쿠키를 지우라는 응답
    assert count(pg, "sessions") == 1
    assert shape(client.post("/auth/logout")) == (401, None, "login_required")  # 이 기기는 끝났다
    assert laptop.post("/auth/logout").status_code == 204  # 다른 기기는 유지됐다


def test_logout_without_login_is_login_required(client):
    response = client.post("/auth/logout")
    assert shape(response) == (401, None, "login_required")
    assert response.json()["message"] == "다시 로그인해 주세요."


def test_logout_after_30_minutes_is_login_required(client, pg):
    client.post("/auth/signup", json=CRED)
    pg.execute("UPDATE sessions SET last_used_at = now() - interval '31 minutes'")
    pg.commit()
    assert shape(client.post("/auth/logout")) == (401, None, "login_required")
    assert count(pg, "sessions") == 0


# ---- 기존 식품 넘겨받기 (D-042 ~ D-045) -------------------------------------------------------------
# 옛 식품은 알렘빅 버전(0002~0004)이 이전용 계정 것으로 가져와 둔다. 첫 가입자가 그 식품을 넘겨받는다.
def legacy_owner(pg):
    return str(pg.execute("SELECT id FROM users WHERE email = 'legacy@fridge.invalid'").fetchone()["id"])


def put_legacy_foods(pg):
    owner = legacy_owner(pg)
    ids = []
    for name, status, processed in [("양파", "none", None), ("우유", "eaten", "2026-10-30")]:
        row = pg.execute(
            "INSERT INTO foods (user_id, name, storage, quantity, unit, purchase_date, expiry_date, source, status, processed_date)"
            " VALUES (%s, %s, 'room', 1, '개', '2026-10-01', '2026-12-01', 'manual', %s, %s) RETURNING id",
            (owner, name, status, processed),
        ).fetchone()
        ids.append(str(row["id"]))
    pg.commit()
    return ids


def user_id(pg, email):
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])


def test_first_signup_gets_legacy_foods_and_second_does_not(client, make_client, pg):
    active, done = put_legacy_foods(pg)
    assert client.post("/auth/signup", json=CRED).status_code == 201
    assert [f["id"] for f in client.get("/foods").json()["items"]] == [active]
    assert [f["id"] for f in client.get("/records/foods").json()["eaten"]] == [done]  # 처리한 식품도 기록에 보인다

    other = make_client()
    other.post("/auth/signup", json={"email": "lee@example.com", "password": CRED["password"]})
    assert other.get("/foods").json()["items"] == []  # 이후 가입은 빈 상태 (D-044)
    assert count(pg, "foods") == 2
    assert pg.execute("SELECT count(*) AS n FROM foods WHERE user_id = %s", (legacy_owner(pg),)).fetchone()["n"] == 0


def test_signup_without_legacy_foods_is_fine(client, pg):
    assert client.post("/auth/signup", json=CRED).status_code == 201
    assert client.get("/foods").json()["items"] == []


def test_failed_signup_leaves_the_legacy_foods_with_the_legacy_account(client, pg, monkeypatch):
    put_legacy_foods(pg)

    def boom(*args, **kwargs):
        raise psycopg.OperationalError("db is down")

    monkeypatch.setattr(legacy_migration, "claim_legacy_foods", boom)
    response = client.post("/auth/signup", json=CRED)
    assert shape(response) == (500, None, "server_error")  # 넘기기는 가입과 같은 묶음이라 가입도 취소된다
    assert real_users(pg) == 0 and count(pg, "sessions") == 0  # 이전용 계정만 있다
    assert pg.execute("SELECT count(*) AS n FROM foods WHERE user_id = %s", (legacy_owner(pg),)).fetchone()["n"] == 2
    monkeypatch.undo()
    assert client.post("/auth/signup", json=CRED).status_code == 201  # 다시 가입하면 받는다
    assert len(client.get("/foods").json()["items"]) == 1


def test_nobody_can_log_in_as_the_legacy_account(client):
    for password in ("!", "", "Passw0rd!"):
        response = client.post("/auth/login", json={"email": "legacy@fridge.invalid", "password": password})
        assert shape(response) == (401, None, "login_failed")


def test_legacy_email_cannot_be_signed_up_again(client, pg):
    response = client.post("/auth/signup", json={"email": "legacy@fridge.invalid", "password": CRED["password"]})
    assert shape(response) == (409, "email", "email_taken")
