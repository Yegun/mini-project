from datetime import date
from typing import Any, Mapping

# 상태 값. 여유·주의·임박·지남 (D-014). API 로 내보내는 영어 값은 사용자가 정했다.
FRESH = "fresh"  # 여유
WARNING = "warning"  # 주의
SOON = "soon"  # 임박
EXPIRED = "expired"  # 지남


def days_left(expiry_date: date, today: date) -> int:
    """남은 날 = 기한 - 오늘. 기한이 지났으면 음수."""
    return (expiry_date - today).days


def status_of(left: int) -> str:
    """남은 날로 상태를 정한다 (D-014)."""
    if left >= 6:
        return FRESH
    if left >= 3:
        return WARNING
    if left >= 0:
        return SOON
    return EXPIRED


def show_on_calendar(left: int) -> bool:
    """지난 지 4일 이상이면 달력에서만 뺀다. 목록에는 남는다 (D-014)."""
    return left > -4


def sort_key(food: Mapping[str, Any]) -> tuple:
    """기한 빠른 순 -> 구매일 이른 순 -> 이름순 (D-015, D-033)."""
    return (food["expiry_date"], food["purchase_date"], food["name"])
