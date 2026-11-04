"""오류를 화면에 알리는 방법을 한 곳에 모았다 (D-008, API-SPEC 0-2절, 3절).

오류는 항상 세 칸이다: field(문제가 된 칸, 없으면 null), reason(이유), message(쉬운 문구).
이유별 상태 번호는 STATUS, 문구는 MESSAGES 한 곳에서만 고친다.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.validation import ValidationError

logger = logging.getLogger(__name__)

# 이유 30개와 상태 번호 (API-SPEC 3절). 입력 오류 422, 없는 식품 404, 기한 다시 적기·중복 가입 409, 로그인 401, 실패 500.
STATUS = {
    "login_failed": 401,
    "login_required": 401,
    "email_taken": 409,
    "weak_password": 422,
    "not_found": 404,
    "expiry_required": 409,
    "invalid_email": 422,
    "required": 422,
    "invalid_quantity": 422,
    "invalid_date": 422,
    "invalid_storage": 422,
    "invalid_status": 422,
    "rule_not_found": 422,
    "rule_name_exists": 422,
    "storage_not_allowed": 422,
    "expiry_input_invalid": 422,
    "invalid_expiry_in_days": 422,
    "expiry_in_past": 422,
    "purchase_after_expiry": 422,
    "rename_expired_not_allowed": 422,
    "storage_change_not_allowed": 422,
    "password_mismatch": 422,
    "invalid_meal": 422,
    "invalid_cuisine": 422,
    "invalid_cuisine_text": 422,
    "photo_invalid": 422,
    "analysis_expired": 422,
    "invalid_item": 422,
    "ai_failed": 502,
    "server_error": 500,
}

LABELS = {
    "name": "이름",
    "unit": "단위",
    "quantity": "수량",
    "purchase_date": "구매일",
    "expiry_date": "기한",
    "expiry_in_days": "며칠 뒤",
    "storage": "보관 방법",
    "status": "처리 방법",
    "email": "이메일",
    "password": "비밀번호",
    "q": "검색어",
    "image": "사진",
    "items": "식품 목록",
    "item_no": "줄 번호",
    "meal": "끼니",
    "cuisine": "음식 종류",
    "cuisine_text": "음식 종류",
}

# 이유별 문구. {label} 은 문제가 된 칸의 한글 이름으로 바뀐다.
MESSAGES = {
    "login_failed": "이메일 또는 비밀번호가 맞지 않아요.",
    "login_required": "다시 로그인해 주세요.",
    "email_taken": "이미 가입된 이메일이에요.",
    "weak_password": "비밀번호는 8자 이상이고 영문·숫자·특수문자를 모두 넣어 주세요.",
    "not_found": "찾을 수 없는 식품이에요.",
    "expiry_required": "기한을 다시 적어 주세요.",
    "invalid_email": "이메일 모양이 올바르지 않아요.",
    "required": "{label} 칸을 채워 주세요.",
    "invalid_quantity": "수량은 0보다 크고 소수 둘째 자리까지, 99999999.99 이하로 적어 주세요.",
    "invalid_date": "{label} 날짜가 올바르지 않아요.",
    "invalid_storage": "보관 방법을 상온·냉장·냉동 중에서 골라 주세요.",
    "invalid_status": "처리 방법이 올바르지 않아요.",
    "rule_not_found": "목록에 없는 식품이에요. 직접 등록으로 등록해 주세요.",
    "rule_name_exists": "목록에 있는 식품이에요. 목록에서 골라 등록해 주세요.",
    "storage_not_allowed": "이 식품은 이 보관 방법을 쓸 수 없어요.",
    "expiry_input_invalid": "기한은 날짜나 며칠 뒤 중 하나만 적어 주세요.",
    "invalid_expiry_in_days": "며칠 뒤는 0 이상의 정수로 적어 주세요.",
    "expiry_in_past": "기한은 오늘 이후 날짜로 적어 주세요.",
    "purchase_after_expiry": "구매일이 기한보다 늦을 수 없어요.",
    "rename_expired_not_allowed": "기한이 지난 식품은 목록에 없는 이름으로 바꿀 수 없어요.",
    "storage_change_not_allowed": "이 보관 방법으로 바꾸면 기한이 지나 버려서 바꿀 수 없어요.",
    "password_mismatch": "비밀번호가 맞지 않아요.",
    "invalid_meal": "끼니를 아침·점심·저녁 중에서 골라 주세요.",
    "invalid_cuisine": "음식 종류를 골라 주세요.",
    "invalid_cuisine_text": "음식 종류를 30자 이내로 적어 주세요.",
    "photo_invalid": "사진은 jpg · png · webp 형식이고 5MB 이하여야 해요.",
    "analysis_expired": "사진을 다시 올려 주세요.",
    "invalid_item": "읽은 식품의 줄 번호가 올바르지 않아요. 사진을 다시 올려 주세요.",
    "ai_failed": "AI 가 응답하지 못했어요. 다시 시도해 주세요.",
    "server_error": "처리하지 못했어요. 잠시 뒤에 다시 해 주세요.",
}

# 같은 이유라도 칸에 따라 문구가 달라야 하는 경우 (A6 의 rule_not_found 는 이름이 아니라 보관 방법 칸이다)
FIELD_MESSAGES = {
    ("rule_not_found", "storage"): "이 식품의 보관 정보를 찾을 수 없어요.",
}


def _base_field(field: str | None) -> str | None:
    """한꺼번에 등록의 줄 오류 칸 이름(items.2.quantity)에서 칸 이름(quantity)만 꺼낸다 (API-SPEC 0-2절)."""
    if field and field.startswith("items.") and field.count(".") == 2:
        return field.rsplit(".", 1)[-1]
    return field


def message_for(reason: str, field: str | None = None) -> str:
    field = _base_field(field)
    if (reason, field) in FIELD_MESSAGES:
        return FIELD_MESSAGES[(reason, field)]
    label = LABELS.get(field, "입력한")
    return MESSAGES[reason].format(label=label)


class ApiError(Exception):
    """화면에 오류로 알릴 일이 생겼을 때 낸다. 상태 번호는 이유에서 정해진다."""

    def __init__(self, reason: str, field: str | None = None):
        if reason not in STATUS:
            raise ValueError(f"정해지지 않은 오류 이유: {reason}")
        super().__init__(reason)
        self.reason = reason
        self.field = field

    @property
    def status_code(self) -> int:
        return STATUS[self.reason]


def error_response(reason: str, field: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=STATUS[reason],
        content={"field": field, "reason": reason, "message": message_for(reason, field)},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(exc.reason, exc.field)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        return error_response(exc.reason, exc.field)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError):
        # 본문이 JSON 객체가 아니는 등 문서에 이유가 없는 경우. FastAPI 기본 모양(detail 목록)은 쓰지 않고
        # 같은 세 칸으로 돌려준다. 이유는 required 로 통일한다.
        first = exc.errors()[0] if exc.errors() else {}
        loc = first.get("loc", ())
        field = loc[-1] if len(loc) > 1 and isinstance(loc[-1], str) else None
        return error_response("required", field)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("처리하지 못한 오류", exc_info=exc)
        return error_response("server_error")
