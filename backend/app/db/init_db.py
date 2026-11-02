"""표를 만들고 규칙표를 채운다. 여러 번 실행해도 같은 결과다 (식품·계정 데이터는 건드리지 않는다).

사용: backend 폴더에서  python -m app.db.init_db      (DATABASE_ADMIN_URL 로 연결)
"""
from app.db.connection import connect_admin
from app.db.migrate import apply_migrations
from app.db.seed_rules import seed_rules


def init_db() -> None:
    """표를 만들고(이미 있으면 건너뜀) 규칙표를 새로 채운다."""
    conn = connect_admin()
    try:
        applied = apply_migrations(conn)
        seed_rules(conn)
        conn.commit()
    finally:
        conn.close()
    print("표 만들기: " + (", ".join(applied) if applied else "이미 최신"))
    print("규칙표 채우기: 완료")


def ensure_db() -> None:
    """서버가 켜질 때 부를 수 있다. 표가 없으면 만들고, 규칙표가 비어 있으면 채운다.

    init_db 는 규칙표를 지우고 다시 채우므로, 이미 규칙표가 있으면 건드리지 않는다 (D-007).
    개발자 계정(DATABASE_ADMIN_URL)이 필요하다. 서버 운영 중에는 부르지 않아도 된다.
    """
    conn = connect_admin()
    try:
        apply_migrations(conn)
        empty = conn.execute("SELECT count(*) AS n FROM rules").fetchone()["n"] == 0
        if empty:
            seed_rules(conn)
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
