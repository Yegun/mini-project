"""오류 모양 (API-SPEC 0-2절, 3절). 이유 27개의 상태 번호·문구, 같은 세 칸, 예상 못 한 오류."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import MESSAGES, STATUS, ApiError, message_for, register_error_handlers
from app.validation import ValidationError

# API-SPEC 3절 표 그대로 (이유, 상태 번호)
SPEC = {
    "login_failed": 401, "login_required": 401, "email_taken": 409, "weak_password": 422,
    "not_found": 404, "expiry_required": 409, "invalid_email": 422, "required": 422,
    "invalid_quantity": 422, "invalid_date": 422, "invalid_storage": 422, "invalid_status": 422,
    "rule_not_found": 422, "rule_name_exists": 422, "storage_not_allowed": 422,
    "expiry_input_invalid": 422, "invalid_expiry_in_days": 422, "expiry_in_past": 422,
    "purchase_after_expiry": 422, "rename_expired_not_allowed": 422,
    "storage_change_not_allowed": 422, "password_mismatch": 422, "invalid_meal": 422, "invalid_cuisine": 422,
    "invalid_cuisine_text": 422, "ai_failed": 502, "server_error": 500,
}


def test_status_table_matches_the_spec():
    assert STATUS == SPEC and len(SPEC) == 27


def test_every_reason_has_a_message():
    assert set(MESSAGES) == set(SPEC)
    for reason in SPEC:
        text = message_for(reason, "name")
        assert text and "{" not in text


def test_fixed_messages_from_the_documents():
    assert message_for("login_failed") == "이메일 또는 비밀번호가 맞지 않아요."
    assert message_for("login_required") == "다시 로그인해 주세요."
    assert message_for("email_taken") == "이미 가입된 이메일이에요."
    assert message_for("weak_password") == "비밀번호는 8자 이상이고 영문·숫자·특수문자를 모두 넣어 주세요."
    assert message_for("not_found") == "찾을 수 없는 식품이에요."
    assert message_for("ai_failed") == "AI 가 응답하지 못했어요. 다시 시도해 주세요."


def test_label_follows_the_field():
    assert message_for("required", "unit") == "단위 칸을 채워 주세요."
    assert message_for("invalid_date", "purchase_date") == "구매일 날짜가 올바르지 않아요."
    assert message_for("invalid_date", "expiry_date") == "기한 날짜가 올바르지 않아요."
    assert message_for("rule_not_found", "storage") != message_for("rule_not_found", "name")


def test_unknown_reason_is_a_programming_error():
    with pytest.raises(ValueError):
        ApiError("not_a_reason")


class Body(BaseModel):
    count: int


def make_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/api-error")
    def api_error():
        raise ApiError("expiry_required", "expiry_date")

    @app.get("/validation")
    def validation():
        raise ValidationError("quantity", "invalid_quantity")

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    @app.post("/body")
    def body(item: Body):
        return item

    return app


@pytest.fixture
def client():
    return TestClient(make_app(), raise_server_exceptions=False)


def test_api_error_has_three_fields_and_its_status(client):
    response = client.get("/api-error")
    assert response.status_code == 409
    assert response.json() == {"field": "expiry_date", "reason": "expiry_required", "message": "기한을 다시 적어 주세요."}


def test_validation_error_is_422(client):
    response = client.get("/validation")
    assert response.status_code == 422
    assert set(response.json()) == {"field", "reason", "message"}
    assert response.json()["field"] == "quantity" and response.json()["reason"] == "invalid_quantity"


def test_unexpected_error_is_server_error_without_details(client):
    response = client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {"field": None, "reason": "server_error", "message": MESSAGES["server_error"]}
    assert "secret" not in response.text


def test_malformed_body_uses_the_same_three_fields(client):
    response = client.post("/body", json={"count": "x"})
    assert response.status_code == 422
    assert set(response.json()) == {"field", "reason", "message"}
    assert response.json()["field"] == "count"
