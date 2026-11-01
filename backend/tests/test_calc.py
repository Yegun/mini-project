from datetime import date

import pytest

from app.calc import (
    expiry_from_days,
    new_expiry_after_storage_change,
    remaining_days_after_storage_change,
    shift_expiry,
)

TODAY = date(2026, 10, 30)


# 기한 = 구매일 + 보관 일수 (V-08). "며칠 뒤" = 구매일 + N일 (D-002)
def test_expiry_from_days_rule_food():
    assert expiry_from_days(date(2026, 10, 30), 7) == date(2026, 11, 6)


def test_expiry_from_days_manual_n_days():
    assert expiry_from_days(date(2026, 10, 30), 3) == date(2026, 11, 2)


def test_expiry_from_days_zero_is_purchase_day():
    assert expiry_from_days(date(2026, 10, 30), 0) == date(2026, 10, 30)


# 구매일을 고치면 기한도 같은 일수만큼 옮긴다 (D-024)
def test_shift_expiry_later_purchase():
    result = shift_expiry(
        old_expiry=date(2026, 11, 6),
        old_purchase=date(2026, 10, 30),
        new_purchase=date(2026, 11, 1),
    )
    assert result == date(2026, 11, 8)


def test_shift_expiry_earlier_purchase():
    result = shift_expiry(
        old_expiry=date(2026, 11, 6),
        old_purchase=date(2026, 10, 30),
        new_purchase=date(2026, 10, 28),
    )
    assert result == date(2026, 11, 4)


# 보관 방법을 바꾸면 지금까지 쓴 비율을 새 방법에 환산한다 (D-006)
# 새 남은 기간 = (1 - 보관한 기간 / 지금 방법 최대) * 새 방법 최대, 소수는 내림 (D-004)
def test_remaining_days_example_fridge_to_freezer():
    # 냉장 10일 중 4일 보관 -> 냉동 30일 기준 (1 - 4/10) * 30 = 18일
    purchase = date(2026, 10, 26)  # 오늘(10/30) 기준 4일 보관
    assert remaining_days_after_storage_change(purchase, TODAY, 10, 30) == 18


def test_remaining_days_rounds_down():
    # (1 - 2/7) * 30 = 21.43 -> 21
    purchase = date(2026, 10, 28)  # 2일 보관
    assert remaining_days_after_storage_change(purchase, TODAY, 7, 30) == 21


def test_remaining_days_future_purchase_counts_as_zero_elapsed():
    # 구매일이 미래면 보관한 기간은 0일 (D-022) -> 새 방법 최대 기간 그대로
    purchase = date(2026, 11, 2)
    assert remaining_days_after_storage_change(purchase, TODAY, 10, 30) == 30


def test_remaining_days_negative_when_past_max():
    # 냉장 10일인데 12일 보관: (1 - 12/10) * 30 = -6 (막을지는 나중 단계에서 정한다)
    purchase = date(2026, 10, 18)
    assert remaining_days_after_storage_change(purchase, TODAY, 10, 30) == -6


def test_remaining_days_rejects_zero_current_max():
    with pytest.raises(ValueError):
        remaining_days_after_storage_change(date(2026, 10, 26), TODAY, 0, 30)


# 새 기한 = 오늘 + 새 남은 기간
def test_new_expiry_after_storage_change():
    purchase = date(2026, 10, 26)
    assert new_expiry_after_storage_change(purchase, TODAY, 10, 30) == date(2026, 11, 17)


def test_new_expiry_future_purchase_counts_from_purchase_day():
    # 구매일이 미래(11/02)면 보관은 그날부터 시작한다 -> 11/02 + 30일 = 12/02
    # ("오늘 + 30일"로 세면 기한이 구매일보다 앞설 수 있다)
    purchase = date(2026, 11, 2)
    assert new_expiry_after_storage_change(purchase, TODAY, 10, 30) == date(2026, 12, 2)


# 이름을 바꿀 때 "비율 이어받기"도 같은 계산이다 (D-004, OQ-11):
# 지금 이름의 최대 기간(10일)을 새 이름의 같은 보관 방법 최대 기간(20일)으로 환산
def test_name_change_ratio_uses_same_calculation():
    purchase = date(2026, 10, 25)  # 5일 보관 -> (1 - 5/10) * 20 = 10일
    assert remaining_days_after_storage_change(purchase, TODAY, 10, 20) == 10
