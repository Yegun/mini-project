"""계정 탈퇴 (API-SPEC H1, US-025). PostgreSQL 임시 schema 에서 서버 코드를 그대로 지난다."""
import psycopg
import pytest

from app.db import foods_repo, photo_analyses_repo, rules_repo, users_repo
from tests.conftest import food_args

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}
OTHER = {"email": "lee@example.com", "password": "Other1234!"}


def count(pg, table, where="", *params):
    return pg.execute(f"SELECT count(*) AS n FROM {table} {where}", params).fetchone()["n"]


def user_id(pg, email):
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


@pytest.fixture
def me(client, pg):
    """가입해서 로그인한 계정. 식품 2개(하나는 다 먹음으로 처리)와 사진 읽기 결과 한 줄을 갖고 있다."""
    assert client.post("/auth/signup", json=CRED).status_code == 201
    uid = user_id(pg, CRED["email"])
    active = foods_repo.create_food(pg, uid, **food_args(name="양파"))
    done = foods_repo.create_food(pg, uid, **food_args(name="우유"))
    foods_repo.set_status(pg, uid, done["id"], "eaten", "2026-10-30")
    photo_analyses_repo.save_analysis(pg, uid, [])
    pg.commit()
    return {"id": uid, "foods": [active["id"], done["id"]]}


@pytest.fixture
def neighbor(make_client, pg):
    """다른 계정. 탈퇴가 이 계정의 것을 건드리지 않는지 본다."""
    other = make_client()
    assert other.post("/auth/signup", json=OTHER).status_code == 201
    uid = user_id(pg, OTHER["email"])
    foods_repo.create_food(pg, uid, **food_args(name="당근"))
    photo_analyses_repo.save_analysis(pg, uid, [])
    pg.commit()
    return other, uid


# ---- 성공 ---------------------------------------------------------------------------------------
def test_withdraw_deletes_the_account_and_everything_of_it(client, pg, me):
    response = client.post("/account/withdraw", json={"password": CRED["password"]})
    assert response.status_code == 204 and response.content == b""
    assert count(pg, "users", "WHERE email = %s", CRED["email"]) == 0
    assert count(pg, "foods", "WHERE user_id = %s", me["id"]) == 0  # 처리한 식품도 지워진다 (D-127)
    assert count(pg, "photo_analyses", "WHERE user_id = %s", me["id"]) == 0
    assert count(pg, "sessions", "WHERE user_id = %s", me["id"]) == 0


def test_withdraw_ends_this_devices_cookie(client, me):
    response = client.post("/account/withdraw", json={"password": CRED["password"]})
    assert "session=" in response.headers["set-cookie"]  # 쿠키를 지우라는 응답
    assert shape(client.get("/foods")) == (401, None, "login_required")


def test_withdraw_ends_every_device(client, make_client, pg, me):
    phone = make_client()
    assert phone.post("/auth/login", json=CRED).status_code == 200
    assert count(pg, "sessions", "WHERE user_id = %s", me["id"]) == 2
    assert client.post("/account/withdraw", json={"password": CRED["password"]}).status_code == 204
    assert count(pg, "sessions", "WHERE user_id = %s", me["id"]) == 0
    assert shape(phone.get("/foods")) == (401, None, "login_required")  # 다른 기기도 다음 요청에서 끝난다 (D-129)


def test_withdraw_leaves_other_accounts_alone(client, pg, me, neighbor):
    other, other_id = neighbor
    client.post("/account/withdraw", json={"password": CRED["password"]})
    assert count(pg, "users", "WHERE id = %s", other_id) == 1
    assert count(pg, "foods", "WHERE user_id = %s", other_id) == 1
    assert count(pg, "photo_analyses", "WHERE user_id = %s", other_id) == 1
    assert other.get("/foods").status_code == 200  # 다른 계정의 로그인은 그대로다


def test_withdraw_keeps_rules_added_by_the_account(client, pg, me):
    """규칙표에 더해진 식품은 탈퇴해도 남고, 누가 더했는지 기록하지 않는다 (ARCHITECTURE 4-3)."""
    rules_repo.add_rule(
        pg, "닭가슴살", "fridge",
        [{"storage": "room", "allowed": False, "max_days": None},
         {"storage": "fridge", "allowed": True, "max_days": 3},
         {"storage": "freezer", "allowed": True, "max_days": 90}],
    )
    pg.commit()
    client.post("/account/withdraw", json={"password": CRED["password"]})
    assert rules_repo.get_rule_by_name(pg, "닭가슴살") is not None
    assert count(pg, "rules") == 31


def test_withdrawn_email_can_sign_up_again_with_nothing(client, make_client, pg, me):
    client.post("/account/withdraw", json={"password": CRED["password"]})
    again = make_client()
    assert again.post("/auth/signup", json=CRED).status_code == 201  # 탈퇴한 이메일은 다시 가입할 수 있다
    assert again.get("/foods").json()["items"] == []  # 새 계정이고 식품이 없다
    assert user_id(pg, CRED["email"]) != me["id"]


def test_first_account_withdrawing_keeps_the_migration_record(client, pg, me):
    """첫 계정이 탈퇴해도 옮김 기록 줄은 남고 user_id 만 비워진다 (Q-09, D-127)."""
    assert pg.execute("SELECT user_id FROM legacy_migration").fetchone()["user_id"] is not None
    client.post("/account/withdraw", json={"password": CRED["password"]})
    row = pg.execute("SELECT user_id, migrated FROM legacy_migration").fetchone()
    assert row["user_id"] is None


# ---- 비밀번호가 틀림 ----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        {"password": "wrong"},
        {"password": "passw0rd!"},  # 대소문자가 다르다
        {"password": ""},
        {"password": None},
        {"password": 12345},
        {"password": ["Passw0rd!"]},
        {},
    ],
)
def test_wrong_empty_or_missing_password_deletes_nothing(client, pg, me, body):
    response = client.post("/account/withdraw", json=body)
    assert shape(response) == (422, "password", "password_mismatch")
    assert set(response.json()) == {"field", "reason", "message"}
    assert count(pg, "users", "WHERE id = %s", me["id"]) == 1
    assert count(pg, "foods", "WHERE user_id = %s", me["id"]) == 2
    assert count(pg, "photo_analyses", "WHERE user_id = %s", me["id"]) == 1
    assert client.get("/foods").status_code == 200  # 로그인도 그대로다


def test_another_accounts_password_does_not_work(client, pg, me, neighbor):
    response = client.post("/account/withdraw", json={"password": OTHER["password"]})
    assert shape(response) == (422, "password", "password_mismatch")
    assert count(pg, "users", "WHERE id = %s", me["id"]) == 1


def test_withdraw_can_be_retried_after_a_wrong_password(client, pg, me):
    assert client.post("/account/withdraw", json={"password": "wrong"}).status_code == 422
    assert client.post("/account/withdraw", json={"password": CRED["password"]}).status_code == 204
    assert count(pg, "users", "WHERE id = %s", me["id"]) == 0


def test_the_password_is_not_stored_or_returned(client, me):
    response = client.post("/account/withdraw", json={"password": "wrong-Passw0rd!"})
    assert "wrong-Passw0rd!" not in response.text


# ---- 로그인 안 함 ------------------------------------------------------------------------------
def test_withdraw_without_login_is_login_required(client, pg):
    response = client.post("/account/withdraw", json={"password": CRED["password"]})
    assert shape(response) == (401, None, "login_required")


def test_withdraw_after_30_minutes_is_login_required_and_deletes_nothing(client, pg, me):
    pg.execute("UPDATE sessions SET last_used_at = now() - interval '31 minutes'")
    pg.commit()
    assert shape(client.post("/account/withdraw", json={"password": CRED["password"]})) == (401, None, "login_required")
    assert count(pg, "users", "WHERE id = %s", me["id"]) == 1


# ---- 한 묶음: 하나라도 실패하면 아무것도 지워지지 않는다 --------------------------------------------
def test_failure_in_the_middle_deletes_nothing(client, pg, me, monkeypatch):
    real_delete = users_repo.delete_user

    def delete_then_fail(conn, uid):
        real_delete(conn, uid)  # 지운 뒤에 실패한다
        raise psycopg.OperationalError("db went away")

    monkeypatch.setattr(users_repo, "delete_user", delete_then_fail)
    response = client.post("/account/withdraw", json={"password": CRED["password"]})
    assert shape(response) == (500, None, "server_error")
    # 전부 취소되어 계정·식품·사진 읽기 결과·로그인 상태가 모두 남는다 (D-127)
    assert count(pg, "users", "WHERE id = %s", me["id"]) == 1
    assert count(pg, "foods", "WHERE user_id = %s", me["id"]) == 2
    assert count(pg, "photo_analyses", "WHERE user_id = %s", me["id"]) == 1
    assert count(pg, "sessions", "WHERE user_id = %s", me["id"]) == 1
    monkeypatch.undo()
    assert client.get("/foods").status_code == 200  # 로그인도 그대로여서 다시 시도할 수 있다


def test_withdraw_does_not_touch_the_legacy_account(client, pg, me):
    client.post("/account/withdraw", json={"password": CRED["password"]})
    assert count(pg, "users", "WHERE email = 'legacy@fridge.invalid'") == 1


# ---- users_repo ---------------------------------------------------------------------------------
def test_repo_verify_user_password(pg, two_users):
    a, b = two_users
    assert users_repo.verify_user_password(pg, a["id"], "Passw0rd!") is True
    assert users_repo.verify_user_password(pg, a["id"], "wrong") is False
    assert users_repo.verify_user_password(pg, a["id"], "") is False
    assert users_repo.verify_user_password(pg, a["id"], None) is False
    legacy = pg.execute("SELECT id FROM users WHERE email = 'legacy@fridge.invalid'").fetchone()["id"]
    assert users_repo.verify_user_password(pg, str(legacy), "!") is False  # 이전용 계정은 어떤 비밀번호도 안 된다


def test_repo_delete_user(pg, two_users):
    a, b = two_users
    assert users_repo.delete_user(pg, a["id"]) is True
    assert users_repo.delete_user(pg, a["id"]) is False  # 이미 없다
    assert count(pg, "users", "WHERE id = %s", b["id"]) == 1
    pg.rollback()
    assert count(pg, "users", "WHERE id = %s", a["id"]) == 1  # commit 은 부르는 쪽이 한다
