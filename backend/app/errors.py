"""오류를 화면에 알리는 방법을 한 곳에 모았다 (D-008).

오류는 항상 세 칸이다: field(문제가 된 칸, 없으면 null), reason(이유), message(쉬운 문구).
번호는 입력 오류 422, 없는 식품 404, 이미 처리됨·기한 다시 적기 409, 저장/불러오기 실패 500.
문구는 구현 단계에서 쉬운 말로 정하기로 했다 (OQ-03). 문구는 이 파일에서만 고친다.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.validation import ValidationError

LABELS = {
    "name": "이름",
    "unit": "단위",
    "quantity": "수량",
    "purchase_date": "구매일",
    "expiry_date": "기한",
    "storage": "보관 방법",
    "status": "처리 방법",
    "q": "검색어",
}

# 이유별 문구. {label} 은 문제가 된 칸의 한글 이름으로 바뀐다.
MESSAGES = {
    "required": "{label} 칸을 채워 주세요.",
    "invalid": "{label} 값이 올바르지 않아요.",
    "not_positive": "수량은 0보다 커야 해요.",
    "too_many_decimals": "수량은 소수 둘째 자리까지만 쓸 수 있어요.",
    "in_past": "기한은 오늘 이후 날짜로 적어 주세요.",
    "after_expiry": "구매일이 기한보다 늦을 수 없어요.",
    "not_allowed": "이 식품은 이 보관 방법을 쓸 수 없어요.",
    "not_in_rules": "목록에 없는 식품이에요. 직접 등록으로 등록해 주세요.",
    "name_change_blocked": "기한이 지난 식품은 목록에 없는 이름으로 바꿀 수 없어요.",
    "change_blocked": "이 보관 방법으로 바꾸면 기한이 지나 버려서 바꿀 수 없어요.",
    "expiry_required": "기한을 다시 적어 주세요.",
    "not_found": "찾을 수 없는 식품이에요.",
    "already_processed": "이미 처리한 식품이에요.",
    "load_failed": "정보를 불러오지 못했어요. 잠시 뒤에 다시 해 주세요.",
    "save_failed": "저장하지 못했어요. 다시 시도해 주세요.",
}


def message_for(reason: str, field: str | None = None) -> str:
    label = LABELS.get(field, "입력한")
    return MESSAGES.get(reason, MESSAGES["invalid"]).format(label=label)


class ApiError(Exception):
    """화면에 오류로 알릴 일이 생겼을 때 낸다."""

    def __init__(self, status_code: int, reason: str, field: str | None = None):
        super().__init__(reason)
        self.status_code = status_code
        self.reason = reason
        self.field = field


def error_response(status_code: int, reason: str, field: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"field": field, "reason": reason, "message": message_for(reason, field)},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(exc.status_code, exc.reason, exc.field)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        return error_response(422, exc.reason, exc.field)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError):
        # FastAPI 기본 오류 모양(detail 목록)은 쓰지 않고, 같은 세 칸으로 바꿔 돌려준다.
        first = exc.errors()[0] if exc.errors() else {}
        loc = first.get("loc", ())
        field = loc[-1] if len(loc) > 1 and isinstance(loc[-1], str) else None
        reason = "required" if first.get("type") == "missing" else "invalid"
        return error_response(422, reason, field)
