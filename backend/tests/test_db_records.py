"""기록 숫자 저장소 (PostgreSQL). 올해·이번 달, 종류 수, 보관별 수, 계정 분리를 본다."""
from conftest import food_args

from app.db.foods_repo import create_food, delete_food, restore_food, set_status
from app.db.records_repo import records_summary

TODAY = "2026-11-02"


def add(pg, user, status="none", day=None, **over):
    food = create_food(pg, user["id"], **food_args(**over))
    if status != "none":
        set_status(pg, user["id"], food["id"], status, day or TODAY)
    return food


def test_all_zero_when_nothing(pg, two_users):
    a, _ = two_users
    assert records_summary(pg, a["id"], TODAY) == {
        "eaten": {"year": 0, "month": 0},
        "discarded": {"year": 0, "month": 0},
        "food_kinds": 0,
        "by_storage": {"room": 0, "fridge": 0, "freezer": 0},
        "expiry_dates": [],
    }


def test_year_and_month_counts_use_processed_date(pg, two_users):
    a, _ = two_users
    add(pg, a, "eaten", "2026-11-01")  # 이번 달
    add(pg, a, "eaten", "2026-11-30")  # 이번 달 (미래 날짜라도 같은 달)
    add(pg, a, "eaten", "2026-10-31")  # 올해, 지난달
    add(pg, a, "eaten", "2026-01-01")  # 올해 첫날
    add(pg, a, "eaten", "2025-12-31")  # 작년
    add(pg, a, "discarded", "2026-11-02")
    add(pg, a, "discarded", "2025-11-02")  # 작년 같은 달
    summary = records_summary(pg, a["id"], TODAY)
    assert summary["eaten"] == {"year": 4, "month": 2}
    assert summary["discarded"] == {"year": 1, "month": 1}


def test_december_month_range(pg, two_users):
    a, _ = two_users
    add(pg, a, "eaten", "2026-12-31")
    add(pg, a, "eaten", "2027-01-01")
    summary = records_summary(pg, a["id"], "2026-12-15")
    assert summary["eaten"] == {"year": 1, "month": 1}


def test_food_kinds_counts_same_name_once_and_only_current(pg, two_users):
    a, _ = two_users
    add(pg, a, name="우유")
    add(pg, a, name="우유")
    add(pg, a, name="두부")
    add(pg, a, "eaten", name="달걀")  # 처리한 식품은 현재 식품이 아니다
    assert records_summary(pg, a["id"], TODAY)["food_kinds"] == 2


def test_same_name_must_match_exactly_to_be_one_kind(pg, two_users):
    a, _ = two_users
    add(pg, a, name="우유")
    add(pg, a, name="우유 ")  # 글자가 완전히 같을 때만 한 종류 (D1)
    assert records_summary(pg, a["id"], TODAY)["food_kinds"] == 2


def test_by_storage_counts_current_foods_only(pg, two_users):
    a, _ = two_users
    add(pg, a, storage="room")
    add(pg, a, storage="fridge")
    add(pg, a, storage="fridge")
    add(pg, a, "discarded", storage="freezer")
    assert records_summary(pg, a["id"], TODAY)["by_storage"] == {"room": 1, "fridge": 2, "freezer": 0}


def test_expiry_dates_include_long_expired_foods(pg, two_users):
    """달력에서 빠진(지난 지 4일 이상) 식품의 기한도 담는다. 판정은 API 가 status.py 로 한다 (API-SPEC 5절 13번)."""
    a, _ = two_users
    add(pg, a, purchase_date="2026-09-01", expiry_date="2026-09-10")  # 지난 지 한참
    add(pg, a, expiry_date="2026-11-05")
    add(pg, a, "eaten", expiry_date="2026-11-30")  # 처리된 식품은 담지 않는다
    assert records_summary(pg, a["id"], TODAY)["expiry_dates"] == ["2026-09-10", "2026-11-05"]


def test_only_my_foods_are_counted(pg, two_users):
    a, b = two_users
    add(pg, a, "eaten", name="내것")
    add(pg, b, "eaten", name="남것")
    add(pg, b, name="남현재")
    summary = records_summary(pg, a["id"], TODAY)
    assert summary["eaten"]["year"] == 1
    assert summary["food_kinds"] == 0 and summary["expiry_dates"] == []


def test_deleted_food_is_not_counted_but_discarded_is(pg, two_users):
    a, _ = two_users
    gone = add(pg, a)
    delete_food(pg, a["id"], gone["id"])
    add(pg, a, "discarded")
    summary = records_summary(pg, a["id"], TODAY)
    assert summary["discarded"]["year"] == 1 and summary["food_kinds"] == 0


def test_restore_removes_food_from_eaten_and_adds_to_current(pg, two_users):
    a, _ = two_users
    food = add(pg, a, "eaten")
    assert records_summary(pg, a["id"], TODAY)["eaten"]["month"] == 1
    restore_food(pg, a["id"], food["id"])
    summary = records_summary(pg, a["id"], TODAY)
    assert summary["eaten"] == {"year": 0, "month": 0}
    assert summary["food_kinds"] == 1


def test_today_may_be_a_date_object(pg, two_users):
    from datetime import date

    a, _ = two_users
    add(pg, a, "eaten", "2026-11-01")
    assert records_summary(pg, a["id"], date(2026, 11, 2))["eaten"]["month"] == 1
