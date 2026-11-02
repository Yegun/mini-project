"""🔒 창구가 모두 쓰는 로그인 확인 (V-19, D-053, API-SPEC 5절 15번). 시험용 작은 서버로 확인한다."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_conn, transaction
from app.db.sessions_repo import create_session
from app.errors import ApiError, register_error_handlers
from app.routers.common import Conn, UserId


@pytest.fixture
def mini(pg, two_users):
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/ping")
    def ping(conn: Conn, user_id: UserId):
        with transaction(conn):
            pass
        return {"user_id": user_id}

    @app.get("/fail")
    def fail(conn: Conn, user_id: UserId):
        with transaction(conn):
            raise ApiError("not_found")

    app.dependency_overrides[get_conn] = lambda: pg
    a, _ = two_users
    token = create_session(pg, a["id"])
    pg.commit()
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set("session", token)
    return client, a, token


def last_used(pg):
    return pg.execute("SELECT last_used_at FROM sessions").fetchone()["last_used_at"]


def age(pg, minutes):
    pg.execute("UPDATE sessions SET last_used_at = now() - make_interval(mins => %s)", (minutes,))
    pg.commit()


def test_valid_cookie_gives_the_account(mini):
    client, a, _ = mini
    assert client.get("/ping").json() == {"user_id": a["id"]}


@pytest.mark.parametrize("cookie", [None, "", "garbage", "x" * 500])
def test_missing_or_unknown_cookie_is_login_required(mini, cookie):
    client, _, _ = mini
    client.cookies.clear()
    if cookie is not None:
        client.cookies.set("session", cookie)
    response = client.get("/ping")
    assert response.status_code == 401
    assert response.json() == {"field": None, "reason": "login_required", "message": "다시 로그인해 주세요."}


def test_success_refreshes_last_used_time(mini, pg):
    client, _, _ = mini
    age(pg, 29)
    assert client.get("/ping").status_code == 200
    pg.rollback()
    recent = pg.execute(
        "SELECT last_used_at > clock_timestamp() - interval '1 minute' AS ok FROM sessions"
    ).fetchone()["ok"]
    assert recent
    age(pg, 29)
    assert client.get("/ping").status_code == 200  # 갱신 덕분에 계속 쓸 수 있다


def test_after_30_minutes_rejected_and_row_removed_for_good(mini, pg):
    client, _, _ = mini
    age(pg, 31)
    assert client.get("/ping").status_code == 401
    pg.rollback()  # 지운 줄이 commit 됐다면 rollback 해도 없다
    assert pg.execute("SELECT count(*) AS n FROM sessions").fetchone()["n"] == 0
    assert client.get("/ping").status_code == 401  # 거절된 요청이 되살리지 않는다


def test_failed_request_does_not_refresh(mini, pg):
    """요청이 실패해 되돌려지면 마지막 사용 시각 갱신도 되돌려진다 (성공할 때만 갱신)."""
    client, _, _ = mini
    age(pg, 29)
    before = last_used(pg)
    assert client.get("/fail").status_code == 404
    pg.rollback()
    assert last_used(pg) == before


def test_account_deleted_means_login_required(mini, pg):
    client, a, _ = mini
    pg.execute("DELETE FROM users WHERE id = %s", (a["id"],))
    pg.commit()
    assert client.get("/ping").status_code == 401
