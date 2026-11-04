"""식품 표 읽기·쓰기. 저장만 하고 규칙 판단(기한 계산, 상태 판정, 입력 검사)은 하지 않는다 (ARCHITECTURE 5절).

- 모든 함수에 계정 번호(user_id)가 붙는다. 없는 식품·남의 식품·(홈·상세에서) 처리된 식품은 똑같이
  None / False 다 (D-061, D-063, D-091). 존재·주인·상태 확인과 변경은 한 문장으로 한다.
- 날짜는 `"2026-10-30"` 글자로 주고받고, 수량은 숫자(float)로 돌려준다. DB 에는 DATE·NUMERIC 으로 저장된다.
- 번호 모양이 UUID 가 아니면 DB 에 보내지 않고 없는 식품으로 본다 (API-SPEC 5절 14번).
- commit 은 하지 않는다. 부르는 쪽이 요청 하나를 한 묶음으로 commit / rollback 한다.
- 응답에는 위험 여부·위험 이유·종류가 붙는다. 저장하지 않고 읽을 때 규칙표를 이름으로 이어서 가져온다 (D-164).
  규칙표 식품(source = rule)은 같은 이름의 규칙표 값, 직접 등록 식품은 위험 아님과 foods.category 에 저장된 값이다.
  규칙표에서 이름을 찾지 못한 규칙표 식품은 위험 아님, 종류 None 이다 (API-SPEC 0-1절).
- 잘못된 값(수량 0 이하, 구매일 > 기한 등)은 DB 가 한 번 더 막고 psycopg.errors.CheckViolation 을 낸다.
  API 검사를 통과한 값이 걸렸다면 API 쪽 검사가 빠진 것이므로 server_error 로 다룬다 (DATA-MODEL 6-5).
"""
import uuid
from datetime import date

import psycopg

# update_food 로 고칠 수 있는 칸. id, user_id, status, processed_date 는 못 바꾼다.
_UPDATABLE = ("name", "storage", "quantity", "unit", "purchase_date", "expiry_date", "source", "category")
_DATE_FIELDS = ("purchase_date", "expiry_date")

# 읽을 때: 식품(f)에 규칙표(r)를 이름으로 이어 위험 여부·이유·종류를 붙인다. {src} 는 식품 표 또는 쓰기 결과(WITH 문)다.
_SELECT = (
    "SELECT f.id, f.name, f.storage, f.quantity, f.unit, f.purchase_date, f.expiry_date, f.source, f.status,"
    " f.processed_date, COALESCE(r.is_danger, false) AS is_danger,"
    " CASE WHEN r.is_danger THEN r.danger_note END AS danger_note,"
    " CASE WHEN f.source = 'manual' THEN f.category ELSE r.category END AS category"
    " FROM {src} f LEFT JOIN rules r ON f.source = 'rule' AND r.name = f.name"
)
_RETURNING = (
    "id, name, storage, quantity, unit, purchase_date, expiry_date, source, status, processed_date, category"
)


def _written(write_sql: str) -> str:
    """INSERT/UPDATE 문(RETURNING 포함)을 실행하고 같은 모양으로 읽는다."""
    return f"WITH w AS ({write_sql}) " + _SELECT.format(src="w")
# 이름순은 글자 코드 순으로 고정한다 (Q-23)
_HOME_ORDER = 'ORDER BY f.expiry_date, f.purchase_date, f.name COLLATE "C", f.id'


def _uuid(value) -> str | None:
    """UUID 모양이면 글자 36자로, 아니면 None (없는 식품으로 본다)."""
    try:
        return str(uuid.UUID(str(value)))
    except ValueError:
        return None


def _food(row: dict | None) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    result["id"] = str(result["id"])
    result["quantity"] = float(result["quantity"])
    for key in ("purchase_date", "expiry_date", "processed_date"):
        if result[key] is not None:
            result[key] = result[key].isoformat()
    return result


def _db_value(key: str, value):
    return date.fromisoformat(value) if key in _DATE_FIELDS and isinstance(value, str) else value


def create_food(
    conn: psycopg.Connection,
    user_id: str,
    *,
    name: str,
    storage: str,
    quantity: float,
    unit: str,
    purchase_date: str,
    expiry_date: str,
    source: str,
    category: str | None = None,
) -> dict:
    """내 식품으로 만든다. 번호는 DB 가 만들고, 처리 상태는 none, 처리한 날짜는 비운다.

    category 는 직접 등록 식품(source = manual)만 저장한다. 규칙표 식품은 None 이다 (DB 규칙, DATA-MODEL 2절).
    """
    row = conn.execute(
        _written(
            "INSERT INTO foods (user_id, name, storage, quantity, unit, purchase_date, expiry_date, source, category)"
            f" VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING {_RETURNING}"
        ),
        (
            user_id, name, storage, str(quantity), unit,
            date.fromisoformat(purchase_date), date.fromisoformat(expiry_date), source, category,
        ),
    ).fetchone()
    return _food(row)


def get_food(
    conn: psycopg.Connection, user_id: str, food_id: str, *, include_processed: bool = False
) -> dict | None:
    """내 식품 한 건. 기본은 처리 상태가 none 인 것만 (처리된 식품은 없는 것처럼 None)."""
    food_id = _uuid(food_id)
    if food_id is None:
        return None
    sql = _SELECT.format(src="foods") + " WHERE f.id = %s AND f.user_id = %s"
    if not include_processed:
        sql += " AND f.status = 'none'"
    return _food(conn.execute(sql, (food_id, user_id)).fetchone())


def list_active_foods(conn: psycopg.Connection, user_id: str) -> list[dict]:
    """홈 목록용. 내 식품 중 처리 상태 none 만, 기한 빠른 순 → 구매일 이른 순 → 이름순 (D-015, D-033)."""
    rows = conn.execute(
        _SELECT.format(src="foods") + f" WHERE f.user_id = %s AND f.status = 'none' {_HOME_ORDER}",
        (user_id,),
    ).fetchall()
    return [_food(r) for r in rows]


def update_food(conn: psycopg.Connection, user_id: str, food_id: str, **fields) -> dict | None:
    """처리 전 내 식품의 칸을 고친다. 없거나 남의 것이거나 처리됐으면 None. 고칠 칸이 없으면 그대로 돌려준다."""
    unknown = set(fields) - set(_UPDATABLE)
    if unknown:
        raise ValueError(f"고칠 수 없는 칸: {sorted(unknown)}")
    if not fields:
        return get_food(conn, user_id, food_id)
    food_id = _uuid(food_id)
    if food_id is None:
        return None
    assignments = ", ".join(f"{col} = %s" for col in fields)  # col 은 위에서 거른 고정 이름만
    values = [str(v) if k == "quantity" else _db_value(k, v) for k, v in fields.items()]
    row = conn.execute(
        _written(
            f"UPDATE foods SET {assignments} WHERE id = %s AND user_id = %s AND status = 'none'"
            f" RETURNING {_RETURNING}"
        ),
        (*values, food_id, user_id),
    ).fetchone()
    return _food(row)


def set_status(
    conn: psycopg.Connection, user_id: str, food_id: str, status: str, processed_date: str
) -> dict | None:
    """다 먹음(eaten) / 버림(discarded) 처리. 행은 남기고 처리한 날짜를 저장한다 (D-064).

    processed_date 는 API 가 정한 오늘(get_today, 한국 시간)이다. DB 시계를 쓰지 않는다 (D-088).
    없거나 남의 것이거나 이미 처리됐으면 None. status 가 eaten/discarded 가 아니면 ValueError.
    """
    if status not in ("eaten", "discarded"):
        raise ValueError("status 는 eaten 또는 discarded 만 가능하다")
    food_id = _uuid(food_id)
    if food_id is None:
        return None
    row = conn.execute(
        _written(
            "UPDATE foods SET status = %s, processed_date = %s"
            f" WHERE id = %s AND user_id = %s AND status = 'none' RETURNING {_RETURNING}"
        ),
        (status, date.fromisoformat(processed_date), food_id, user_id),
    ).fetchone()
    return _food(row)


def restore_food(conn: psycopg.Connection, user_id: str, food_id: str) -> dict | None:
    """홈으로 되돌리기 (D3). 처리 상태 none, 처리한 날짜 비움. 나머지 칸은 그대로 (D-075, D-076).

    없거나 남의 것이거나 처리되지 않은 식품이면 None.
    """
    food_id = _uuid(food_id)
    if food_id is None:
        return None
    row = conn.execute(
        _written(
            "UPDATE foods SET status = 'none', processed_date = NULL"
            f" WHERE id = %s AND user_id = %s AND status <> 'none' RETURNING {_RETURNING}"
        ),
        (food_id, user_id),
    ).fetchone()
    return _food(row)


def delete_food(conn: psycopg.Connection, user_id: str, food_id: str) -> bool:
    """처리 전 내 식품의 행을 완전히 지운다. 되돌리기 없음. 없거나 남의 것이거나 처리됐으면 False (D-091)."""
    food_id = _uuid(food_id)
    if food_id is None:
        return False
    cur = conn.execute(
        "DELETE FROM foods WHERE id = %s AND user_id = %s AND status = 'none'", (food_id, user_id)
    )
    return cur.rowcount > 0


def list_processed_for_advice(conn: psycopg.Connection, user_id: str, limit: int) -> list[dict]:
    """기록 조언(I1)용. 내 식품 중 처리한 것(다 먹음·버림)을 최근 처리한 순으로 limit 개까지 준다.

    줄마다 name, status(eaten/discarded), processed_date, expiry_date 만 준다. 수량·구매일은 AI 에게 보내지 않으므로 읽지 않는다 (D-163).
    """
    rows = conn.execute(
        "SELECT name, status, processed_date, expiry_date FROM foods"
        " WHERE user_id = %s AND status <> 'none'"
        ' ORDER BY processed_date DESC, name COLLATE "C", id LIMIT %s',
        (user_id, limit),
    ).fetchall()
    return [
        {
            "name": row["name"],
            "status": row["status"],
            "processed_date": row["processed_date"].isoformat(),
            "expiry_date": row["expiry_date"].isoformat(),
        }
        for row in rows
    ]


def list_processed_foods(conn: psycopg.Connection, user_id: str) -> dict[str, list[dict]]:
    """기록 화면의 처리한 식품 목록 (D2). 다 먹음 / 버림을 나눠, 최근 처리한 순 → 이름순 (D-073, D-074).

    줄마다 id, name, quantity, unit, processed_date, category 를 준다. category 는 홈 목록과 같은 방식으로 붙인다.
    """
    rows = conn.execute(
        "SELECT f.id, f.name, f.quantity, f.unit, f.status, f.processed_date,"
        " CASE WHEN f.source = 'manual' THEN f.category ELSE r.category END AS category"
        " FROM foods f LEFT JOIN rules r ON f.source = 'rule' AND r.name = f.name"
        " WHERE f.user_id = %s AND f.status <> 'none'"
        ' ORDER BY f.processed_date DESC, f.name COLLATE "C", f.id',
        (user_id,),
    ).fetchall()
    result: dict[str, list[dict]] = {"eaten": [], "discarded": []}
    for row in rows:
        result[row["status"]].append(
            {
                "id": str(row["id"]),
                "name": row["name"],
                "quantity": float(row["quantity"]),
                "unit": row["unit"],
                "processed_date": row["processed_date"].isoformat(),
                "category": row["category"],
            }
        )
    return result
