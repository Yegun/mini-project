"""기록 숫자 (D1, US-013). 저장하지 않고 요청할 때마다 foods 로 센다 (ARCHITECTURE 3절, D-065 ~ D-069).

- 내 식품만 센다. 삭제한 식품은 행이 없어서 어떤 숫자에도 들어가지 않는다 (D-070).
- "오늘"은 인자로 받는다. DB 시계(CURRENT_DATE)는 쓰지 않는다 (D-088). 올해·이번 달은 처리한 날짜 기준이다 (D-066).
- 식품 상태별 수(여유·주의·임박·지남)의 판정은 홈 목록과 같은 판정(app/status.py)을 API 가 해야 하므로
  (ARCHITECTURE 5절, D-009), 여기서는 처리 전 식품의 기한 목록(expiry_dates)만 준다.
  지난 지 4일 이상 식품도 빼지 않고 모두 담는다 (API-SPEC 5절 13번).
- 처리한 식품 목록(D2)은 foods_repo.list_processed_foods 에 있다.
"""
from datetime import date

import psycopg


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def records_summary(conn: psycopg.Connection, user_id: str, today) -> dict:
    """모양:
    {"eaten": {"year", "month"}, "discarded": {"year", "month"}, "food_kinds": int,
     "by_storage": {"room", "fridge", "freezer"}, "expiry_dates": ["YYYY-MM-DD", ...]}
    """
    today = _as_date(today)
    year_start = date(today.year, 1, 1)
    next_year = date(today.year + 1, 1, 1)
    month_start = today.replace(day=1)
    next_month = date(today.year + (today.month == 12), today.month % 12 + 1, 1)

    row = conn.execute(
        "SELECT"
        " count(*) FILTER (WHERE status = 'eaten' AND processed_date >= %(ys)s AND processed_date < %(ny)s) AS eaten_year,"
        " count(*) FILTER (WHERE status = 'eaten' AND processed_date >= %(ms)s AND processed_date < %(nm)s) AS eaten_month,"
        " count(*) FILTER (WHERE status = 'discarded' AND processed_date >= %(ys)s AND processed_date < %(ny)s) AS discarded_year,"
        " count(*) FILTER (WHERE status = 'discarded' AND processed_date >= %(ms)s AND processed_date < %(nm)s) AS discarded_month,"
        " count(DISTINCT name) FILTER (WHERE status = 'none') AS food_kinds,"
        " count(*) FILTER (WHERE status = 'none' AND storage = 'room') AS room,"
        " count(*) FILTER (WHERE status = 'none' AND storage = 'fridge') AS fridge,"
        " count(*) FILTER (WHERE status = 'none' AND storage = 'freezer') AS freezer"
        " FROM foods WHERE user_id = %(user)s",
        {"ys": year_start, "ny": next_year, "ms": month_start, "nm": next_month, "user": user_id},
    ).fetchone()
    expiry_rows = conn.execute(
        "SELECT expiry_date FROM foods WHERE user_id = %s AND status = 'none' ORDER BY expiry_date",
        (user_id,),
    ).fetchall()
    return {
        "eaten": {"year": row["eaten_year"], "month": row["eaten_month"]},
        "discarded": {"year": row["discarded_year"], "month": row["discarded_month"]},
        "food_kinds": row["food_kinds"],
        "by_storage": {"room": row["room"], "fridge": row["fridge"], "freezer": row["freezer"]},
        "expiry_dates": [r["expiry_date"].isoformat() for r in expiry_rows],
    }
