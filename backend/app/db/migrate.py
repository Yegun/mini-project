"""표를 만든다. migrations/ 의 .sql 파일을 번호 순서대로 한 번씩만 실행한다 (Q-21).

실행한 파일 이름은 schema_migrations 표에 적어 둔다. 여러 번 실행해도 이미 한 것은 건너뛴다.
파일 하나는 한 묶음이다. 중간에 실패하면 그 파일은 아무것도 바뀌지 않는다.

사용: backend 폴더에서  python -m app.db.migrate      (DATABASE_ADMIN_URL 로 연결)
"""
from pathlib import Path

import psycopg

from app.db.connection import connect_admin

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def apply_migrations(conn: psycopg.Connection) -> list[str]:
    """아직 실행하지 않은 파일을 실행하고, 실행한 파일 이름을 돌려준다. 끝나면 commit 한다."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    conn.commit()
    done = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    conn.commit()

    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        try:
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied.append(path.name)
    return applied


def main() -> None:
    conn = connect_admin()
    try:
        applied = apply_migrations(conn)
    finally:
        conn.close()
    if applied:
        print("실행함: " + ", ".join(applied))
    else:
        print("새로 실행할 파일이 없다 (이미 최신).")


if __name__ == "__main__":
    main()
