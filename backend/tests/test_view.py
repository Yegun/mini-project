"""식품 응답 모양 (API-SPEC 0-1절)."""
from datetime import date

from app.view import food_json

TODAY = date(2026, 10, 30)

KEYS = {
    "id", "name", "storage", "quantity", "unit", "purchase_date", "expiry_date", "source", "status",
    "processed_date", "expiry_status", "days_left", "show_on_calendar", "is_danger", "danger_note", "category",
}


def food(**over):
    data = dict(
        id="0b0e0b8e-3f4b-4f43-9f0a-5d5b0d9b3b11", user_id="ignored", name="우유", storage="fridge",
        quantity=1.5, unit="L", purchase_date="2026-10-28", expiry_date="2026-11-04", source="rule",
        status="none", processed_date=None, is_danger=False, danger_note=None, category="other",
    )
    data.update(over)
    return data


def test_has_exactly_the_spec_fields_and_hides_owner():
    result = food_json(food(), TODAY)
    assert set(result) == KEYS
    assert "user_id" not in result


def test_computed_fields_for_active_food():
    result = food_json(food(expiry_date="2026-11-04"), TODAY)  # 5일 남음 = 주의
    assert (result["expiry_status"], result["days_left"], result["show_on_calendar"]) == ("warning", 5, True)
    assert result["processed_date"] is None
    assert result["purchase_date"] == "2026-10-28" and result["quantity"] == 1.5


def test_status_boundaries_and_calendar():
    cases = {
        "2026-11-05": ("fresh", 6, True),
        "2026-11-04": ("warning", 5, True),
        "2026-11-02": ("warning", 3, True),
        "2026-11-01": ("soon", 2, True),
        "2026-10-30": ("soon", 0, True),  # 기한 당일
        "2026-10-29": ("expired", -1, True),
        "2026-10-27": ("expired", -3, True),
        "2026-10-26": ("expired", -4, False),  # 지난 지 4일 이상은 달력에서만 뺀다
    }
    for expiry, expected in cases.items():
        r = food_json(food(purchase_date="2026-10-01", expiry_date=expiry), TODAY)
        assert (r["expiry_status"], r["days_left"], r["show_on_calendar"]) == expected, expiry


def test_processed_food_has_null_computed_fields_and_keeps_date():
    for status in ("eaten", "discarded"):
        r = food_json(food(status=status, processed_date="2026-10-30"), TODAY)
        assert (r["expiry_status"], r["days_left"], r["show_on_calendar"]) == (None, None, None)
        assert r["processed_date"] == "2026-10-30" and r["status"] == status


def test_danger_note_and_category_are_passed_through_as_the_repository_read_them():
    result = food_json(food(name="닭고기", is_danger=True, danger_note="덜 익히면 위험해요", category="meat"), TODAY)
    assert (result["is_danger"], result["danger_note"], result["category"]) == (True, "덜 익히면 위험해요", "meat")


def test_danger_and_category_stay_on_processed_foods():
    result = food_json(
        food(status="eaten", processed_date="2026-10-29", is_danger=True, danger_note="이유", category="seafood"), TODAY
    )
    assert result["expiry_status"] is None and result["days_left"] is None and result["show_on_calendar"] is None
    assert (result["is_danger"], result["danger_note"], result["category"]) == (True, "이유", "seafood")  # 계산 칸이 아니다
