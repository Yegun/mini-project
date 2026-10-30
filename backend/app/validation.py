import re
from collections.abc import Collection
from datetime import date
from decimal import Decimal

from app.calc import expiry_from_days

# 칸 이름은 DATA-MODEL.md (D-032) 의 이름을 쓴다.
STORAGES = ("room", "fridge", "freezer")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(Exception):
    """입력 규칙을 어겼을 때 낸다.

    field: 문제가 된 칸 이름
    reason: 이유. 이 문서 안에서만 쓰는 이름이고, API 로 내보낼 오류 모양은 아직 정해지지 않았다.
    """

    def __init__(self, field: str, reason: str):
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


def validate_text(value, field: str) -> str:
    """V-01 이름·단위는 비면 안 된다. 글자는 그대로 돌려준다."""
    if value is None:
        raise ValidationError(field, "required")
    if not isinstance(value, str):
        raise ValidationError(field, "invalid")
    if value.strip() == "":
        raise ValidationError(field, "required")
    return value


def validate_quantity(value) -> Decimal:
    """V-02 수량은 0보다 큰 숫자, 소수 둘째 자리까지 (D-027)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValidationError("quantity", "invalid")
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if not number.is_finite():
        raise ValidationError("quantity", "invalid")
    if number <= 0:
        raise ValidationError("quantity", "not_positive")
    if number.as_tuple().exponent < -2:
        raise ValidationError("quantity", "too_many_decimals")
    return number


def parse_date(value, field: str) -> date:
    """V-03 올바른 날짜인지 확인한다. 날짜 글자는 YYYY-MM-DD (D-031). 미래도 괜찮다."""
    if value is None or value == "":
        raise ValidationError(field, "required")
    if type(value) is date:
        return value
    if isinstance(value, str) and _DATE_PATTERN.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValidationError(field, "invalid")


def validate_storage(value) -> str:
    """보관 방법은 상온·냉장·냉동 중 하나 (D-032)."""
    if value is None or value == "":
        raise ValidationError("storage", "required")
    if value not in STORAGES:
        raise ValidationError("storage", "invalid")
    return value


def validate_storage_allowed(storage: str, allowed: Collection[str]) -> None:
    """V-04 규칙표가 "불가"로 정한 보관 방법은 고를 수 없다 (D-005)."""
    if storage not in allowed:
        raise ValidationError("storage", "not_allowed")


def check_expiry_not_in_past(expiry_date: date, today: date) -> None:
    """V-05 기한은 오늘보다 과거일 수 없다. 오늘은 괜찮다."""
    if expiry_date < today:
        raise ValidationError("expiry_date", "in_past")


def check_purchase_not_after_expiry(purchase_date: date, expiry_date: date) -> None:
    """V-07 구매일이 기한보다 뒤인 조합은 막는다 (D-003). 같은 날은 괜찮다."""
    if purchase_date > expiry_date:
        raise ValidationError("purchase_date", "after_expiry")


def resolve_manual_expiry(
    purchase_date: date, expiry_date, days_from_purchase, today: date
) -> date:
    """직접 등록의 기한을 정한다 (US-003).

    날짜로 고르거나, 며칠 뒤(구매일 + N일, D-002)로 적는다. 둘 중 하나만 있어야 한다.
    """
    has_date = expiry_date is not None and expiry_date != ""
    has_days = days_from_purchase is not None
    if not has_date and not has_days:
        raise ValidationError("expiry_date", "required")
    if has_date and has_days:
        raise ValidationError("expiry_date", "invalid")

    if has_date:
        expiry = parse_date(expiry_date, "expiry_date")
    else:
        if (
            isinstance(days_from_purchase, bool)
            or not isinstance(days_from_purchase, int)
            or days_from_purchase < 0
        ):
            raise ValidationError("expiry_date", "invalid")
        expiry = expiry_from_days(purchase_date, days_from_purchase)

    check_expiry_not_in_past(expiry, today)
    check_purchase_not_after_expiry(purchase_date, expiry)
    return expiry
