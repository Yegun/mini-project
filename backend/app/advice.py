"""기록 조언 규칙 (API-SPEC 2-9절 I1, ARCHITECTURE V-37, 3-1, D-159 ~ D-163).

내 식품(처리 전 + 처리한 것)을 AI 에게 보내 기록과 지금 상태를 함께 본 조언을 받는다. 결과는 저장하지 않는다 (D-161).
AI 에게는 식품 이름·상태·남은 날, 처리 종류·처리한 날짜·기한만 보낸다. 이메일·계정 번호·수량·구매일은 보내지 않는다 (D-163).
AI 의 답은 믿지 않고 서버가 모양을 검사한다. 모양이 틀리면 ai_failed 다.
"""
from datetime import date

from app import ai
from app.errors import ApiError
from app.status import days_left, status_of

# 처리한 식품은 최근 처리한 것부터 이만큼만 보낸다. 개수는 구현 단계에서 정한다 (ARCHITECTURE 3-1).
PROCESSED_LIMIT = 100


def build_material(active_foods: list[dict], processed_foods: list[dict], today: date) -> dict:
    """AI 에게 보낼 자료. active_foods 는 처리 전 식품, processed_foods 는 처리한 식품이다."""
    active = []
    for food in active_foods:
        left = days_left(date.fromisoformat(food["expiry_date"]), today)
        active.append({"name": food["name"], "status": status_of(left), "days_left": left})
    processed = [
        {
            "name": food["name"],
            "result": food["status"],
            "processed_date": food["processed_date"],
            "expiry_date": food["expiry_date"],
        }
        for food in processed_foods
    ]
    return {"active": active, "processed": processed}


def _read_advice(answer) -> list[str]:
    """V-37. 글 목록이고 비어 있지 않아야 한다. 아니면 ai_failed (V-30)."""
    if not isinstance(answer, dict) or not isinstance(answer.get("advice"), list) or not answer["advice"]:
        raise ApiError("ai_failed")
    advice = []
    for text in answer["advice"]:
        if not isinstance(text, str) or not text.strip():
            raise ApiError("ai_failed")
        advice.append(text.strip())
    return advice


def advise(active_foods: list[dict], processed_foods: list[dict], today: date) -> dict:
    """I1. 식품도 처리한 기록도 하나도 없으면 AI 를 부르지 않고 no_data 로 돌려준다 (V-37). 실패가 아니다."""
    if not active_foods and not processed_foods:
        return {"advice": [], "reason": "no_data"}
    answer = ai.give_advice(build_material(active_foods, processed_foods, today))
    return {"advice": _read_advice(answer), "reason": None}
