"""기존 식품(v0.2.0, SQLite) 옮기기 (D-042 ~ D-045, D-097 ~ D-099, DATA-MODEL 7절).

- 처음 가입하는 계정이 만들어지는 순간 한 번만 그 계정으로 옮긴다. 이후 가입하는 계정은 빈 상태다.
- legacy_migration 표에는 한 줄만 있다. 줄이 없으면 아직 아무도 가입하지 않은 것이다 (첫 가입이 줄을 만든다).
- 묶음 두 개 (DATA-MODEL 7-3):
    ① register_first_user  가입 묶음 안에서 부른다. 첫 계정이면 줄을 만든다 (migrated = 거짓).
    ② migrate_legacy_foods  옮김. 식품 복사 전부 + migrated = 참 이 한 묶음(savepoint)이다.
       실패하면 ②만 취소되고 가입·로그인은 유지된다 (D-097). 부르는 쪽이 실패를 알리지 않고 넘어가도 된다.
- 옮긴 뒤에도 SQLite 파일은 지우지 않고 백업으로 남긴다. 읽기 전용으로만 연다 (D-098).
- 옮길 식품이 없거나 SQLite 파일이 없으면 곧바로 migrated = 참 으로 끝난다.
- commit 은 하지 않는다.
"""
import sqlite3
from datetime import date
from pathlib import Path

import psycopg

from app.db.connection import foods_db_path, savepoint

_COLUMNS = "id, name, storage, quantity, unit, purchase_date, expiry_date, source, status"


def register_first_user(conn: psycopg.Connection, user_id: str) -> bool:
    """가입 묶음 안에서 부른다. 첫 계정이면 옮김 기록 줄을 만들고 True, 이미 첫 계정이 정해졌으면 False.

    두 사람이 동시에 처음 가입해도 id = 1 한 줄만 만들어진다.
    """
    cur = conn.execute(
        "INSERT INTO legacy_migration (id, user_id, migrated) VALUES (1, %s, false)"
        " ON CONFLICT (id) DO NOTHING",
        (user_id,),
    )
    return cur.rowcount == 1


def needs_migration(conn: psycopg.Connection, user_id: str) -> bool:
    """로그인할 때 부른다. 이 계정이 첫 계정이고 아직 옮기지 못했으면 True (D-097)."""
    row = conn.execute(
        "SELECT 1 FROM legacy_migration WHERE id = 1 AND user_id = %s AND NOT migrated", (user_id,)
    ).fetchone()
    return row is not None


def _read_legacy_foods(path: Path) -> list[sqlite3.Row]:
    if not path.is_file():
        return []
    legacy = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)  # 읽기 전용 (D-098)
    legacy.row_factory = sqlite3.Row
    try:
        return legacy.execute(f"SELECT {_COLUMNS} FROM foods").fetchall()
    except sqlite3.OperationalError:  # foods 표가 없다 = 옮길 것이 없다
        return []
    finally:
        legacy.close()


def migrate_legacy_foods(
    conn: psycopg.Connection, user_id: str, today, *, legacy_path: Path | None = None
) -> bool:
    """첫 계정에게 기존 식품을 옮긴다. 성공하면 True, 옮길 차례가 아니면 False.

    실패하면 ② 묶음만 취소하고 예외를 그대로 낸다. 가입·로그인 묶음은 건드리지 않는다.
    today 는 API 가 정한 오늘(한국 시간)이다. 이미 처리된 식품의 처리한 날짜가 된다 (D-045).
    같은 줄을 잠가서 두 기기에서 동시에 로그인해도 두 번 옮기지 않는다.
    """
    today = today if isinstance(today, date) else date.fromisoformat(today)
    rows = _read_legacy_foods(Path(legacy_path) if legacy_path else foods_db_path())
    with savepoint(conn):  # 안에서 실패하면 여기까지만 되돌린다
        locked = conn.execute(
            "SELECT 1 FROM legacy_migration WHERE id = 1 AND user_id = %s AND NOT migrated FOR UPDATE",
            (user_id,),
        ).fetchone()
        if locked is None:
            return False
        for r in rows:
            processed = None if r["status"] == "none" else today
            conn.execute(
                "INSERT INTO foods (id, user_id, name, storage, quantity, unit, purchase_date, expiry_date,"
                " source, status, processed_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    r["id"], user_id, r["name"], r["storage"], str(r["quantity"]), r["unit"],
                    date.fromisoformat(r["purchase_date"]), date.fromisoformat(r["expiry_date"]),
                    r["source"], r["status"], processed,
                ),
            )
        conn.execute("UPDATE legacy_migration SET migrated = true WHERE id = 1")
    return True
