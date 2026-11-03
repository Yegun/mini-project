"""계정 창구 (API-SPEC 2-7절 H1, US-025)."""
from typing import Any

from fastapi import APIRouter, Response

from app.auth import COOKIE_NAME
from app.database import transaction
from app.db import users_repo
from app.errors import ApiError
from app.routers.common import Body, Conn, UserId

router = APIRouter()


class WithdrawBody(Body):
    password: Any = None


@router.post("/account/withdraw", status_code=204)
def withdraw(body: WithdrawBody, conn: Conn, user_id: UserId):
    """H1 탈퇴 🔒. 비밀번호가 맞으면 이 계정을 지운다 (D-127, D-128).

    한 묶음으로 계정의 식품(처리한 식품 포함), 사진 읽기 결과, 모든 기기의 로그인 상태, 계정을 지운다 (D-129).
    하나라도 실패하면 전부 취소되어 아무것도 지워지지 않는다. 규칙표에 더해진 식품은 지우지 않는다.
    비밀번호가 틀리거나 비었거나 안 보냈으면 password_mismatch 422 이고 아무것도 지우지 않는다.
    """
    with transaction(conn):
        if not users_repo.verify_user_password(conn, user_id, body.password):
            raise ApiError("password_mismatch", "password")
        users_repo.delete_user(conn, user_id)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME)  # 이 기기의 쿠키도 끝낸다. 다른 기기는 다음 요청에서 login_required 가 된다
    return response
