"""식품을 화면에 내보내는 모양으로 바꾼다."""

from datetime import date

from app.status import days_left, show_on_calendar, status_of


def food_json(food: dict, today: date) -> dict:
    """DB 칸에 계산 값 3개(expiry_status, days_left, show_on_calendar)를 붙인다.

    상태는 API 가 계산하고 화면은 색만 입힌다 (D-009). 처리된 식품은 계산 값이 null 이다.
    """
    result = {
        "id": food["id"],
        "name": food["name"],
        "storage": food["storage"],
        "quantity": food["quantity"],
        "unit": food["unit"],
        "purchase_date": food["purchase_date"].isoformat(),
        "expiry_date": food["expiry_date"].isoformat(),
        "source": food["source"],
        "status": food["status"],
        "expiry_status": None,
        "days_left": None,
        "show_on_calendar": None,
    }
    if food["status"] == "none":
        left = days_left(food["expiry_date"], today)
        result["expiry_status"] = status_of(left)
        result["days_left"] = left
        result["show_on_calendar"] = show_on_calendar(left)
    return result
