from datetime import date
from decimal import Decimal

import pytest

from app.validation import (
    ValidationError,
    check_expiry_not_in_past,
    check_purchase_not_after_expiry,
    parse_date,
    resolve_manual_expiry,
    validate_email,
    validate_password,
    validate_quantity,
    validate_status,
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


# V-01 이름·단위는 비면 안 된다. 앞뒤 공백은 지우고 저장한다 (DATA-MODEL Q-06)
def test_text_ok_is_trimmed():
    assert validate_text("두부", "name") == "두부"
    assert validate_text(" 1봉 ", "unit") == "1봉"


def test_text_blank_is_required():
    assert fail(validate_text, "", "name") == ("name", "required")
    assert fail(validate_text, "   ", "unit") == ("unit", "required")
    assert fail(validate_text, None, "name") == ("name", "required")
    assert fail(validate_text, 123, "name") == ("name", "required")


# V-02 수량은 0보다 큰 숫자, 소수 둘째 자리까지, 정수 8자리까지. 모두 invalid_quantity
def test_quantity_ok():
    assert validate_quantity(1) == Decimal("1")
    assert validate_quantity(0.25) == Decimal("0.25")
    assert validate_quantity(Decimal("2.50")) == Decimal("2.50")
    assert validate_quantity(99999999.99) == Decimal("99999999.99")


@pytest.mark.parametrize(
    "value", [0, -1, 1.234, 0.001, 100000000, "2", None, True, float("nan"), float("inf")]
)
def test_quantity_bad_values(value):
    assert fail(validate_quantity, value) == ("quantity", "invalid_quantity")


# V-03 구매일은 올바른 날짜 (미래 가능). 날짜는 YYYY-MM-DD 글자 (D-031). 모두 invalid_date
def test_parse_date_ok():
    assert parse_date("2026-10-30", "purchase_date") == date(2026, 10, 30)
    assert parse_date("2027-01-01", "purchase_date") == date(2027, 1, 1)  # 미래 가능
    assert parse_date(date(2026, 10, 30), "purchase_date") == date(2026, 10, 30)


@pytest.mark.parametrize("value", ["2026-02-30", "20261030", "2026-1-5", "내일", 20261030, "", None])
def test_parse_date_bad_values(value):
    assert fail(parse_date, value, "purchase_date") == ("purchase_date", "invalid_date")
    assert fail(parse_date, value, "expiry_date") == ("expiry_date", "invalid_date")


# 보관 방법은 상온·냉장·냉동 셋 중 하나 (D-032)
def test_storage():
    for value in ("room", "fridge", "freezer"):
        assert validate_storage(value) == value
    for value in ("shelf", None, "", 3):
        assert fail(validate_storage, value) == ("storage", "invalid_storage")


def test_status():
    assert validate_status("eaten") == "eaten"
    assert validate_status("discarded") == "discarded"
    for value in ("none", "", None, 1):
        assert fail(validate_status, value) == ("status", "invalid_status")


# V-04 규칙표가 "불가"로 정한 보관 방법은 고를 수 없다 (D-005)
def test_storage_allowed_check():
    validate_storage_allowed("fridge", {"fridge", "freezer"})
    assert fail(validate_storage_allowed, "room", {"fridge", "freezer"}) == (
        "storage",
        "storage_not_allowed",
    )


# V-05 기한은 오늘보다 과거일 수 없다. 오늘은 괜찮다
def test_expiry_not_in_past():
    check_expiry_not_in_past(TODAY, TODAY)
    check_expiry_not_in_past(date(2026, 11, 1), TODAY)
    assert fail(check_expiry_not_in_past, date(2026, 10, 29), TODAY) == ("expiry_date", "expiry_in_past")


# V-07 구매일이 기한보다 뒤인 조합은 막는다 (D-003). 같은 날은 괜찮다
def test_purchase_not_after_expiry():
    check_purchase_not_after_expiry(date(2026, 10, 30), date(2026, 10, 30))
    check_purchase_not_after_expiry(date(2026, 10, 30), date(2026, 11, 5))
    late, expiry = date(2026, 11, 6), date(2026, 11, 5)
    assert fail(check_purchase_not_after_expiry, late, expiry) == ("expiry_date", "purchase_after_expiry")
    assert fail(check_purchase_not_after_expiry, late, expiry, "purchase_date") == (
        "purchase_date",
        "purchase_after_expiry",
    )


# 직접 등록 기한: 날짜로 고르거나, 며칠 뒤(구매일 + N일)로 적는다 (D-002, V-05, V-06)
def test_manual_expiry_by_date_or_days():
    assert resolve_manual_expiry(date(2026, 10, 30), "2026-11-05", None, TODAY) == date(2026, 11, 5)
    assert resolve_manual_expiry(date(2026, 10, 30), None, 3, TODAY) == date(2026, 11, 2)
    assert resolve_manual_expiry(TODAY, None, 0, TODAY) == TODAY  # 0일 = 구매한 날
    assert resolve_manual_expiry(TODAY, "", 3, TODAY) == date(2026, 11, 2)  # 빈 글자는 안 보낸 것


def test_manual_expiry_needs_exactly_one_input():
    both = ("expiry_date", "expiry_input_invalid")
    assert fail(resolve_manual_expiry, TODAY, None, None, TODAY) == both
    assert fail(resolve_manual_expiry, TODAY, "2026-11-05", 3, TODAY) == both


def test_manual_expiry_bad_date_and_days():
    assert fail(resolve_manual_expiry, TODAY, "2026-02-30", None, TODAY) == ("expiry_date", "invalid_date")
    bad_days = ("expiry_in_days", "invalid_expiry_in_days")
    for days in (-1, 2.5, True, "3"):
        assert fail(resolve_manual_expiry, TODAY, None, days, TODAY) == bad_days


def test_manual_expiry_in_past_is_rejected():
    assert fail(resolve_manual_expiry, TODAY, "2026-10-29", None, TODAY) == ("expiry_date", "expiry_in_past")
    # 구매일이 과거라서 "구매일 + N일"이 오늘보다 앞이 되는 경우도 같다
    assert fail(resolve_manual_expiry, date(2026, 10, 1), None, 5, TODAY) == ("expiry_date", "expiry_in_past")


def test_manual_expiry_before_purchase_is_rejected():
    # 구매일이 미래(11/10)인데 기한이 그보다 앞(11/05)
    assert fail(resolve_manual_expiry, date(2026, 11, 10), "2026-11-05", None, TODAY) == (
        "expiry_date",
        "purchase_after_expiry",
    )


# 이메일은 @ 앞뒤에 글자가 있고 @ 뒤에 점이 있는 모양까지만 (D-096)
@pytest.mark.parametrize("value", ["a@b.co", "kim.lee+x@mail.example.com", "  a@b.c  "])
def test_email_ok(value):
    assert validate_email(value) == value.strip()


@pytest.mark.parametrize(
    "value", ["", "abc", "a@b", "@b.c", "a@.", "a@b.", "a b@c.d", "a@@b.c", "a@b c.d", None, 5]
)
def test_email_bad(value):
    assert fail(validate_email, value) == ("email", "invalid_email")


# 비밀번호: 8자 이상 + 영문·숫자·특수문자 모두. 쓸 수 있는 특수문자는 정해진 기호뿐 (D-047)
@pytest.mark.parametrize("value", ["Passw0rd!", "abcd123$", "A1!aaaaa", "x1-y2_z3", "Ab1/Cd2?"])
def test_password_ok(value):
    assert validate_password(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "Pw0rd!",  # 8자 미만
        "Password!",  # 숫자 없음
        "12345678!",  # 영문 없음
        "Passw0rd1",  # 특수문자 없음
        "Passw0rd! ",  # 공백
        "Passw0rd한!",  # 한글
        "Passw0rd~",  # 목록에 없는 기호
        "",
        None,
        12345678,
    ],
)
def test_password_weak(value):
    assert fail(validate_password, value) == ("password", "weak_password")
