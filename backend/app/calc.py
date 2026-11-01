from datetime import date, timedelta


def expiry_from_days(purchase_date: date, days: int) -> date:
    """기한 = 구매일 + 일수.

    규칙표 등록은 보관 방법별 일수(V-08), 직접 등록의 "며칠 뒤"는 N일(D-002).
    """
    return purchase_date + timedelta(days=days)


def shift_expiry(old_expiry: date, old_purchase: date, new_purchase: date) -> date:
    """구매일을 고치면 기한도 구매일이 움직인 일수만큼 옮긴다 (D-024)."""
    return old_expiry + (new_purchase - old_purchase)


def remaining_days_after_storage_change(
    purchase_date: date, today: date, current_max_days: int, new_max_days: int
) -> int:
    """보관 방법을 바꾼 뒤의 새 남은 기간(일). 음수가 나올 수 있다.

    새 남은 기간 = (1 - 지금까지 보관한 기간 / 지금 방법 최대 기간) * 새 방법 최대 기간
    소수 날짜는 내림한다 (D-004). 구매일이 미래라 보관한 기간이 음수면 0일로 본다 (D-022).
    이름을 바꿀 때의 "비율 이어받기"(D-004, OQ-11)도 같은 계산을 쓴다.
    계산 결과를 막을지는 여기서 정하지 않는다. 숫자만 돌려준다.
    """
    if current_max_days <= 0:
        raise ValueError("current_max_days must be greater than 0")
    elapsed = max((today - purchase_date).days, 0)
    # 소수 오차를 피하려고 정수로만 계산하고, 나눗셈(//)은 내림이다.
    return ((current_max_days - elapsed) * new_max_days) // current_max_days


def new_expiry_after_storage_change(
    purchase_date: date, today: date, current_max_days: int, new_max_days: int
) -> date:
    """새 기한 = 보관 시작점 + 새 남은 기간.

    보관 시작점은 오늘과 구매일 중 늦은 날이다. 구매일이 미래면 그날부터 보관이 시작되고,
    이미 시작했다면 오늘부터 남은 기간을 센다.
    """
    remaining = remaining_days_after_storage_change(
        purchase_date, today, current_max_days, new_max_days
    )
    return max(today, purchase_date) + timedelta(days=remaining)
