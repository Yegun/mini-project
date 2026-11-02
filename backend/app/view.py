"""식품을 화면에 내보내는 모양으로 바꾼다 (API-SPEC 0-1절). 식품을 돌려주는 창구는 모두 이것을 쓴다."""

from datetime import date

from app.status import days_left, show_on_calendar, status_of


def food_json(food: dict, today: date) -> dict:
    """저장소의 식품(날짜는 YYYY-MM-DD 글자)에 계산 값 3개(expiry_status, days_left, show_on_calendar)를 붙인다.

    상태는 API 가 계산하고 화면은 색만 입힌다 (D-009). 처리된 식품은 계산 값이 null 이다.
    주인(user_id)은 내보내지 않는다.
    """
    result = {
        "id": food["id"],
        "name": food["name"],
        "storage": food["storage"],
        "quantity": food["quantity"],
        "unit": food["unit"],
        "purchase_date": food["purchase_date"],
        "expiry_date": food["expiry_date"],
        "source": food["source"],
        "status": food["status"],
        "processed_date": food["processed_date"],
        "expiry_status": None,
        "days_left": None,
        "show_on_calendar": None,
    }
    if food["status"] == "none":
        left = days_left(date.fromisoformat(food["expiry_date"]), today)
        result["expiry_status"] = status_of(left)
        result["days_left"] = left
        result["show_on_calendar"] = show_on_calendar(left)
    return result
