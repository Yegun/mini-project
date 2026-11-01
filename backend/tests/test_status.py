from datetime import date

from app.status import (
    EXPIRED,
    FRESH,
    SOON,
    WARNING,
    days_left,
    show_on_calendar,
    sort_key,
    status_of,
)

TODAY = date(2026, 10, 30)


# 남은 날 = 기한 - 오늘 (D-014)
def test_days_left_tomorrow_is_1():
    assert days_left(date(2026, 10, 31), TODAY) == 1


def test_days_left_today_is_0():
    assert days_left(TODAY, TODAY) == 0


def test_days_left_yesterday_is_minus_1():
    assert days_left(date(2026, 10, 29), TODAY) == -1


# 6일 이상 여유 / 3~5일 주의 / 0~2일 임박 / 기한 다음 날부터 지남 (D-014)
def test_status_boundaries():
    assert status_of(7) == FRESH
    assert status_of(6) == FRESH
    assert status_of(5) == WARNING
    assert status_of(3) == WARNING
    assert status_of(2) == SOON
    assert status_of(0) == SOON
    assert status_of(-1) == EXPIRED
    assert status_of(-10) == EXPIRED


# 지난 지 4일 이상이면 달력에서만 뺀다. 목록에는 남는다 (D-014)
def test_show_on_calendar_boundaries():
    assert show_on_calendar(6) is True
    assert show_on_calendar(0) is True
    assert show_on_calendar(-1) is True
    assert show_on_calendar(-3) is True
    assert show_on_calendar(-4) is False
    assert show_on_calendar(-30) is False


# 기한 빠른 순 -> 같으면 구매일 이른 순 -> 같으면 이름순 (D-015, D-033)
def _food(name, purchase, expiry):
    return {"name": name, "purchase_date": purchase, "expiry_date": expiry}


def test_sort_by_expiry_first():
    a = _food("가", date(2026, 10, 1), date(2026, 11, 5))
    b = _food("나", date(2026, 10, 1), date(2026, 11, 2))
    assert sorted([a, b], key=sort_key) == [b, a]


def test_sort_same_expiry_earlier_purchase_first():
    a = _food("가", date(2026, 10, 20), date(2026, 11, 5))
    b = _food("나", date(2026, 10, 10), date(2026, 11, 5))
    assert sorted([a, b], key=sort_key) == [b, a]


def test_sort_same_expiry_and_purchase_by_name():
    a = _food("두부", date(2026, 10, 10), date(2026, 11, 5))
    b = _food("당근", date(2026, 10, 10), date(2026, 11, 5))
    assert sorted([a, b], key=sort_key) == [b, a]
