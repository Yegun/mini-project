"""옛 식품(v0.2.0, SQLite)을 foods 로 가져오기. 아직 주인 없이

Revision ID: 0002
Revises: 0001

기존 데이터 이전의 둘째 단계다 (D-042, D-045, D-098).
- 읽는 곳: 옛 SQLite 식품 파일 (환경 변수 FRIDGE_DB_PATH, 없으면 backend/data/fridge.db). 읽기 전용으로만 연다.
- 번호(id)는 옛 번호를 그대로 쓴다 (DATA-MODEL Q-17). 주인(user_id)은 비워 둔다. 0003·0004 에서 붙인다.
- 이미 처리한 식품(다 먹음·버림)은 처리한 날짜가 없으므로 **옮긴 날(한국 시간 오늘)** 을 처리한 날로 한다 (D-045).
- 파일이 없거나 식품이 없으면 아무것도 하지 않는다. 이 파일은 파일이 있는 컴퓨터에서 올릴 때만 식품을 가져온다.
- 옮긴 뒤에도 SQLite 파일은 지우지 않고 백업으로 남긴다.
"""
import sqlite3
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INSERT = sa.text(
    "INSERT INTO foods (id, name, storage, quantity, unit, purchase_date, expiry_date, source, status, processed_date)"
    " VALUES (CAST(:id AS uuid), :name, :storage, CAST(:quantity AS numeric), :unit,"
    " CAST(:purchase_date AS date), CAST(:expiry_date AS date), :source, :status, CAST(:processed_date AS date))"
    " ON CONFLICT (id) DO NOTHING"
)


def _read_legacy_foods() -> list[dict]:
    from app.db.connection import foods_db_path  # 파일 위치는 한 곳에서만 정한다

    path = foods_db_path()
    if not path.is_file():
        return []
    legacy = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    legacy.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in legacy.execute(
            "SELECT id, name, storage, quantity, unit, purchase_date, expiry_date, source, status FROM foods"
        )]
    except sqlite3.OperationalError:  # foods 표가 없다 = 옮길 것이 없다
        return []
    finally:
        legacy.close()


def upgrade() -> None:
    from app.database import get_today  # "오늘"은 한 곳에서만 정한다 (D-088)

    rows = _read_legacy_foods()
    if not rows:
        return
    moved_on = get_today().isoformat()
    params = [
        {**row, "quantity": str(row["quantity"]), "processed_date": None if row["status"] == "none" else moved_on}
        for row in rows
    ]
    op.get_bind().execute(INSERT, params)


def downgrade() -> None:
    # 이 시점(0003·0004 가 이미 되돌려진 뒤)에 주인 없는 식품은 가져온 식품뿐이다.
    op.execute("DELETE FROM foods WHERE user_id IS NULL")
