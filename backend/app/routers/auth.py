"""가입 · 로그인 · 로그아웃 창구 (API-SPEC 2-1절, US-012)."""
import logging
from typing import Any

from fastapi import APIRouter, Request, Response

from app.auth import COOKIE_NAME, session_token
from app.database import transaction
from app.db import legacy_migration, sessions_repo, users_repo
from app.errors import ApiError
from app.routers.common import Body, Conn, Today, UserId
from app.validation import validate_email, validate_password

logger = logging.getLogger(__name__)

router = APIRouter()


class Credentials(Body):
    email: Any = None
    password: Any = None


def _set_login_cookie(response: Response, token: str) -> None:
    """쿠키 이름 session, 자바스크립트에서 못 읽게(HttpOnly), 같은 사이트 요청에만(SameSite=Lax). 그 밖의 속성은 정하지 않았다."""
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")


def _try_migrate(conn, user_id: str, today) -> None:
    """기존 식품 옮기기 (D-042, D-097). 가입·로그인은 이미 commit 됐다. 옮기다 실패해도 가입·로그인은 성공이다.

    실패하면 옮김만 취소되고(첫 계정이 다음에 로그인할 때 다시 시도) 오류는 삼킨다.
    """
    try:
        if legacy_migration.migrate_legacy_foods(conn, user_id, today):
            conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("기존 식품 옮기기에 실패했다. 다음 로그인 때 다시 시도한다.")


@router.post("/auth/signup", status_code=201)
def signup(body: Credentials, response: Response, conn: Conn, today: Today):
    """B1 가입. 계정을 만들고 이 기기의 로그인 상태를 만든다. 첫 가입이면 기존 식품을 한 번만 옮긴다."""
    email = validate_email(body.email)
    validate_password(body.password)
    with transaction(conn):
        try:
            user = users_repo.create_user(conn, email, body.password)
        except users_repo.EmailTaken as error:
            raise ApiError("email_taken", "email") from error
        first = legacy_migration.register_first_user(conn, user["id"])
        token = sessions_repo.create_session(conn, user["id"])
    _set_login_cookie(response, token)
    if first:
        _try_migrate(conn, user["id"], today)
    return {"email": user["email"]}


@router.post("/auth/login")
def login(body: Credentials, response: Response, conn: Conn, today: Today):
    """B2 로그인. 이 기기의 로그인 상태를 새로 만든다 (다른 기기는 그대로).

    이메일 모양·비밀번호 규칙은 검사하지 않는다. 맞지 않는 값은 모두 login_failed 다 (V-17, D-057).
    """
    with transaction(conn):
        email, password = body.email, body.password
        user = None
        if isinstance(email, str) and isinstance(password, str):
            user = users_repo.authenticate(conn, email, password)
        if user is None:
            raise ApiError("login_failed")
        token = sessions_repo.create_session(conn, user["id"])
        migrate = legacy_migration.needs_migration(conn, user["id"])
    _set_login_cookie(response, token)
    if migrate:
        _try_migrate(conn, user["id"], today)
    return {"email": user["email"]}


@router.post("/auth/logout", status_code=204)
def logout(request: Request, conn: Conn, user_id: UserId):
    """B3 로그아웃 🔒. 이 기기의 로그인 상태만 끝낸다. 다른 기기는 유지된다 (D-054)."""
    with transaction(conn):
        sessions_repo.delete_session(conn, session_token(request))
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME)
    return response
