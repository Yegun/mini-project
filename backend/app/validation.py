"""입력 검사. 이유 이름과 칸 이름은 API-SPEC 3절을 따른다 (D-010: 최종 판단은 API).

검사에 걸리면 ValidationError(칸, 이유)를 낸다. 422 와 문구는 errors.py 가 붙인다.
"""
import re
import string
from collections.abc import Collection
from datetime import date
from decimal import Decimal

from app.calc import expiry_from_days

# 칸 이름은 DATA-MODEL.md (D-032) 의 이름을 쓴다.
STORAGES = ("room", "fridge", "freezer")
STATUSES = ("eaten", "discarded")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 이메일: @ 앞뒤에 글자가 있고 @ 뒤에 점이 있는 모양까지만 (D-096)
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# 비밀번호에 쓸 수 있는 특수문자 (2026-11-02 사용자 승인). 영문·숫자·이 기호 밖의 글자는 쓸 수 없다.
PASSWORD_SPECIALS = "!@#$%^&*()-_=+[]{};:,.<>/?"
_PASSWORD_LETTERS = set(string.ascii_letters)
_PASSWORD_DIGITS = set(string.digits)
# 수량은 정수 8자리 + 소수 2자리까지 (DATA-MODEL Q-05)
_QUANTITY_LIMIT = Decimal("100000000")


class ValidationError(Exception):
    """입력 규칙을 어겼을 때 낸다 (422).

    field: 문제가 된 칸 이름
    reason: API-SPEC 3절의 이유 이름
    """

    def __init__(self, field: str, reason: str):
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


def validate_text(value, field: str) -> str:
    """V-01 이름·단위는 비면 안 된다. 앞뒤 공백은 지우고 돌려준다 (DATA-MODEL Q-06)."""
    if not isinstance(value, str) or value.strip() == "":
        raise ValidationError(field, "required")
    return value.strip()


def validate_quantity(value) -> Decimal:
    """V-02 수량은 0보다 큰 숫자, 소수 둘째 자리까지, 정수 8자리까지 (D-027, Q-05). 모두 invalid_quantity."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValidationError("quantity", "invalid_quantity")
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if not number.is_finite() or number <= 0 or number >= _QUANTITY_LIMIT:
        raise ValidationError("quantity", "invalid_quantity")
    if number.as_tuple().exponent < -2:
        raise ValidationError("quantity", "invalid_quantity")
    return number


def parse_date(value, field: str) -> date:
    """V-03 올바른 날짜인지 확인한다. 날짜 글자는 YYYY-MM-DD (D-031). 미래도 괜찮다. 비었거나 틀리면 invalid_date."""
    if type(value) is date:
        return value
    if isinstance(value, str) and _DATE_PATTERN.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValidationError(field, "invalid_date")


def validate_storage(value) -> str:
    """보관 방법은 상온·냉장·냉동 중 하나 (D-032). 없거나 다르면 invalid_storage."""
    if not isinstance(value, str) or value not in STORAGES:
        raise ValidationError("storage", "invalid_storage")
    return value


def validate_status(value) -> str:
    """처리 방법은 eaten 또는 discarded."""
    if not isinstance(value, str) or value not in STATUSES:
        raise ValidationError("status", "invalid_status")
    return value


def validate_storage_allowed(storage: str, allowed: Collection[str]) -> None:
    """V-04 규칙표가 "불가"로 정한 보관 방법은 고를 수 없다 (D-005)."""
    if storage not in allowed:
        raise ValidationError("storage", "storage_not_allowed")


def check_expiry_not_in_past(expiry_date: date, today: date) -> None:
    """V-05 기한은 오늘보다 과거일 수 없다. 오늘은 괜찮다."""
    if expiry_date < today:
        raise ValidationError("expiry_date", "expiry_in_past")


def check_purchase_not_after_expiry(
    purchase_date: date, expiry_date: date, field: str = "expiry_date"
) -> None:
    """V-07 구매일이 기한보다 뒤인 조합은 막는다 (D-003). 같은 날은 괜찮다.

    field 는 어느 칸 때문인지다. 기한이 구매일보다 앞이면 expiry_date, 구매일을 기한보다 뒤로 바꾸면 purchase_date.
    """
    if purchase_date > expiry_date:
        raise ValidationError(field, "purchase_after_expiry")


def resolve_manual_expiry(
    purchase_date: date, expiry_date, days_from_purchase, today: date
) -> date:
    """직접 등록의 기한을 정한다 (US-003).

    날짜로 고르거나, 며칠 뒤(구매일 + N일, D-002)로 적는다. 둘 중 하나만 있어야 한다.
    """
    has_date = expiry_date is not None and expiry_date != ""
    has_days = days_from_purchase is not None
    if has_date == has_days:  # 둘 다 없거나 둘 다 있음
        raise ValidationError("expiry_date", "expiry_input_invalid")

    if has_date:
        expiry = parse_date(expiry_date, "expiry_date")
    else:
        if (
            isinstance(days_from_purchase, bool)
            or not isinstance(days_from_purchase, int)
            or days_from_purchase < 0
        ):
            raise ValidationError("expiry_in_days", "invalid_expiry_in_days")
        expiry = expiry_from_days(purchase_date, days_from_purchase)

    check_expiry_not_in_past(expiry, today)
    check_purchase_not_after_expiry(purchase_date, expiry)
    return expiry


def validate_email(value) -> str:
    """V-15 이전의 모양 확인 (D-096). 앞뒤 공백은 지우고 돌려준다. 소문자로 바꾸는 것은 저장소가 한다."""
    if not isinstance(value, str) or not _EMAIL_PATTERN.match(value.strip()):
        raise ValidationError("email", "invalid_email")
    return value.strip()


def validate_password(value) -> str:
    """V-15 비밀번호는 8자 이상이고 영문·숫자·특수문자를 모두 포함 (D-047).

    쓸 수 있는 글자는 영문·숫자·PASSWORD_SPECIALS 뿐이다. 그 밖의 글자(한글, 공백)가 있으면 weak_password.
    로그인에서는 이 검사를 하지 않는다 (API-SPEC 5절 12번).
    """
    if not isinstance(value, str) or len(value) < 8:
        raise ValidationError("password", "weak_password")
    chars = set(value)
    if not chars <= (_PASSWORD_LETTERS | _PASSWORD_DIGITS | set(PASSWORD_SPECIALS)):
        raise ValidationError("password", "weak_password")
    if not (chars & _PASSWORD_LETTERS and chars & _PASSWORD_DIGITS and chars & set(PASSWORD_SPECIALS)):
        raise ValidationError("password", "weak_password")
    return value
