"""앱(API)이 쓰는 DB 계정을 만든다. 이 계정은 규칙표 세 표를 읽기만 할 수 있다 (D-007, Q-16).

- 식품·계정·로그인 상태·옮김 기록 표: 읽기·쓰기 (SELECT, INSERT, UPDATE, DELETE)
- 규칙표 세 표(rules, rule_aliases, rule_storage): 읽기만 (SELECT)
- 표 만들기·규칙표 채우기·기한 다시 계산은 이 계정으로 못 한다. 개발자 계정(DATABASE_ADMIN_URL)을 쓴다.

비밀번호는 .env 에서만 읽는다 (Git 과 채팅에 쓰지 않는다).
  APP_DB_USER      만들 앱 계정 이름
  APP_DB_PASSWORD  그 계정의 비밀번호
여러 번 실행해도 같은 결과다 (이미 있으면 비밀번호와 권한만 다시 맞춘다).

사용: backend 폴더에서  python -m app.db.setup_roles   (DATABASE_ADMIN_URL 로 연결)
수파베이스에서는 계정 이름 규칙(연결 문자열의 사용자 이름) 때문에 연결 문자열 쪽 확인이 필요할 수 있다.
"""
import psycopg
from psycopg import sql

from app.db.connection import connect_admin, env_value

READ_WRITE = ("users", "sessions", "foods", "legacy_migration")
READ_ONLY = ("rules", "rule_aliases", "rule_storage")


def setup_app_role(conn: psycopg.Connection, user: str, password: str, schema: str = "public") -> None:
    """앱 계정을 만들거나 맞추고 권한을 준다. commit 은 부르는 쪽."""
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,)).fetchone()
    verb = "ALTER" if exists else "CREATE"
    conn.execute(
        sql.SQL(verb + " ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(user), sql.Literal(password))
    )
    role, sch = sql.Identifier(user), sql.Identifier(schema)
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sch, role))
    conn.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}").format(sch, role))
    for table in READ_WRITE:
        conn.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {}.{} TO {}").format(
                sch, sql.Identifier(table), role
            )
        )
    for table in READ_ONLY:
        conn.execute(sql.SQL("GRANT SELECT ON {}.{} TO {}").format(sch, sql.Identifier(table), role))


def main() -> None:
    user = env_value("APP_DB_USER")
    password = env_value("APP_DB_PASSWORD")
    conn = connect_admin()
    try:
        setup_app_role(conn, user, password)
        conn.commit()
    finally:
        conn.close()
    print(f"앱 계정 {user}: 규칙표 읽기 전용, 나머지 표 읽기·쓰기")


if __name__ == "__main__":
    main()
