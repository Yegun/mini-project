from datetime import date
from decimal import Decimal

import pytest

from app.validation import (
    ValidationError,
    check_expiry_not_in_past,
    check_purchase_not_after_expiry,
    parse_date,
    resolve_manual_expiry,
    validate_quantity,
    validate_storage,
    validate_storage_allowed,
    validate_text,
)

TODAY = date(2026, 10, 30)


def fail(func, *args, **kwargs):
    """검사가 ValidationError 를 내는지 확인하고 (칸, 이유)를 돌려준다."""
    with pytest.raises(ValidationError) as info:
        func(*args, **kwargs)
    return info.value.field, info.value.reason


# V-01 이름·단위는 비면 안 된다. 글자는 그대로 둔다 (DATA-MODEL 3-2)
def test_text_ok_is_returned_as_is():
    assert validate_text("두부", "name") == "두부"
    assert validate_text(" 1봉 ", "unit") == " 1봉 "


def test_text_blank_is_rejected():
    assert fail(validate_text, "", "name") == ("name", "required")
    assert fail(validate_text, "   ", "unit") == ("unit", "required")
    assert fail(validate_text, None, "name") == ("name", "required")


def test_text_not_a_string_is_rejected():
    assert fail(validate_text, 123, "name") == ("name", "invalid")


# V-02 수량은 0보다 큰 숫자, 소수 둘째 자리까지 (D-027)
def test_quantity_ok():
    assert validate_quantity(1) == Decimal("1")
    assert validate_quantity(0.25) == Decimal("0.25")
    assert validate_quantity(1.5) == Decimal("1.5")
    assert validate_quantity(Decimal("2.50")) == Decimal("2.50")


def test_quantity_zero_or_negative_is_rejected():
    assert fail(validate_quantity, 0) == ("quantity", "not_positive")
    assert fail(validate_quantity, -1) == ("quantity", "not_positive")


def test_quantity_more_than_two_decimals_is_rejected():
    assert fail(validate_quantity, 1.234) == ("quantity", "too_many_decimals")
    assert fail(validate_quantity, 0.001) == ("quantity", "too_many_decimals")


def test_quantity_not_a_number_is_rejected():
    assert fail(validate_quantity, "2") == ("quantity", "invalid")
    assert fail(validate_quantity, None) == ("quantity", "invalid")
    assert fail(validate_quantity, True) == ("quantity", "invalid")
    assert fail(validate_quantity, float("nan")) == ("quantity", "invalid")
    assert fail(validate_quantity, float("inf")) == ("quantity", "invalid")


# V-03 구매일은 올바른 날짜 (미래 가능). 날짜는 YYYY-MM-DD 글자 (D-031)
def test_parse_date_ok():
    assert parse_date("2026-10-30", "purchase_date") == date(2026, 10, 30)
    assert parse_date("2027-01-01", "purchase_date") == date(2027, 1, 1)  # 미래 가능
    assert parse_date(date(2026, 10, 30), "purchase_date") == date(2026, 10, 30)


def test_parse_date_rejects_bad_values():
    assert fail(parse_date, "2026-02-30", "purchase_date") == ("purchase_date", "invalid")
    assert fail(parse_date, "20261030", "purchase_date") == ("purchase_date", "invalid")
    assert fail(parse_date, "2026-1-5", "purchase_date") == ("purchase_date", "invalid")
    assert fail(parse_date, "내일", "purchase_date") == ("purchase_date", "invalid")
    assert fail(parse_date, 20261030, "purchase_date") == ("purchase_date", "invalid")


def test_parse_date_missing_is_required():
    assert fail(parse_date, None, "purchase_date") == ("purchase_date", "required")
    assert fail(parse_date, "", "purchase_date") == ("purchase_date", "required")


# 보관 방법은 상온·냉장·냉동 셋 중 하나 (D-032)
def test_storage_ok():
    for value in ("room", "fridge", "freezer"):
        assert validate_storage(value) == value


def test_storage_other_value_is_rejected():
    assert fail(validate_storage, "shelf") == ("storage", "invalid")
    assert fail(validate_storage, None) == ("storage", "required")


# V-04 규칙표가 "불가"로 정한 보관 방법은 고를 수 없다 (D-005)
def test_storage_allowed_check():
    validate_storage_allowed("fridge", {"fridge", "freezer"})  # 통과
    assert fail(validate_storage_allowed, "room", {"fridge", "freezer"}) == (
        "storage",
        "not_allowed",
    )


# V-05 기한은 오늘보다 과거일 수 없다. 오늘은 괜찮다
def test_expiry_not_in_past():
    check_expiry_not_in_past(TODAY, TODAY)  # 통과
    check_expiry_not_in_past(date(2026, 11, 1), TODAY)  # 통과
    assert fail(check_expiry_not_in_past, date(2026, 10, 29), TODAY) == (
        "expiry_date",
        "in_past",
    )


# V-07 구매일이 기한보다 뒤인 조합은 막는다 (D-003). 같은 날은 괜찮다
def test_purchase_not_after_expiry():
    check_purchase_not_after_expiry(date(2026, 10, 30), date(2026, 10, 30))  # 통과
    check_purchase_not_after_expiry(date(2026, 10, 30), date(2026, 11, 5))  # 통과
    assert fail(
        check_purchase_not_after_expiry, date(2026, 11, 6), date(2026, 11, 5)
    ) == ("purchase_date", "after_expiry")


# 직접 등록 기한: 날짜로 고르거나, 며칠 뒤(구매일 + N일)로 적는다 (D-002, V-05, V-06)
def test_manual_expiry_by_date():
    result = resolve_manual_expiry(
        purchase_date=date(2026, 10, 30),
        expiry_date="2026-11-05",
        days_from_purchase=None,
        today=TODAY,
    )
    assert result == date(2026, 11, 5)


def test_manual_expiry_by_days_from_purchase():
    result = resolve_manual_expiry(
        purchase_date=date(2026, 10, 30),
        expiry_date=None,
        days_from_purchase=3,
        today=TODAY,
    )
    assert result == date(2026, 11, 2)


def test_manual_expiry_zero_days_means_purchase_day():
    result = resolve_manual_expiry(TODAY, None, 0, TODAY)
    assert result == TODAY


def test_manual_expiry_needs_exactly_one_input():
    assert fail(resolve_manual_expiry, TODAY, None, None, TODAY) == (
        "expiry_date",
        "required",
    )
    assert fail(resolve_manual_expiry, TODAY, "2026-11-05", 3, TODAY) == (
        "expiry_date",
        "invalid",
    )


def test_manual_expiry_days_must_be_whole_non_negative_number():
    assert fail(resolve_manual_expiry, TODAY, None, -1, TODAY) == (
        "expiry_date",
        "invalid",
    )
    assert fail(resolve_manual_expiry, TODAY, None, 2.5, TODAY) == (
        "expiry_date",
        "invalid",
    )
    assert fail(resolve_manual_expiry, TODAY, None, True, TODAY) == (
        "expiry_date",
        "invalid",
    )


def test_manual_expiry_in_past_is_rejected():
    assert fail(resolve_manual_expiry, TODAY, "2026-10-29", None, TODAY) == (
        "expiry_date",
        "in_past",
    )
    # 구매일이 과거라서 "구매일 + N일"이 오늘보다 앞이 되는 경우도 같다
    assert fail(resolve_manual_expiry, date(2026, 10, 1), None, 5, TODAY) == (
        "expiry_date",
        "in_past",
    )


def test_manual_expiry_before_purchase_is_rejected():
    # 구매일이 미래(11/10)인데 기한이 그보다 앞(11/05)
    assert fail(resolve_manual_expiry, date(2026, 11, 10), "2026-11-05", None, TODAY) == (
        "purchase_date",
        "after_expiry",
    )
