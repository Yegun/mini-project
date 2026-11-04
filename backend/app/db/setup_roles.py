"""앱(API)이 쓰는 DB 계정을 만든다. 이 계정은 규칙표에 읽기와 '더하기'만 할 수 있다 (D-007, Q-27).

- 식품·계정·로그인 상태·옮김 기록·사진 읽기 결과 표: 읽기·쓰기 (SELECT, INSERT, UPDATE, DELETE)
- 규칙표 식품(rules)·보관 방법별 정보(rule_storage): 읽기와 더하기 (SELECT, INSERT). 사진으로 한꺼번에 등록할 때
  규칙표에 없는 식품을 더하기 위해서다 (D-136). 이미 있는 줄을 고치거나 지우는 것은 못 한다.
- 별칭(rule_aliases): 읽기만 (SELECT). 사진 등록으로 더해지는 식품은 별칭이 없다 (ARCHITECTURE 4-3).
- 표 만들기·규칙표 채우기·기한 다시 계산은 이 계정으로 못 한다. 개발자 계정(DATABASE_ADMIN_URL)을 쓴다.
- 오늘의 일반 조언(daily_tips): 읽기와 더하기 (SELECT, INSERT). 하루 한 줄을 더하고, 있는 줄을 고치거나 지우지 않는다 (DATA-MODEL 6-1).
- 표 9개에 RLS(줄 단위 보안)가 켜져 있고 정책은 없다 (알렘빅 0008, 0009, Q-33). 앱 계정은 RLS 를 건너뛰는 속성(BYPASSRLS)을 받아야
  읽고 쓸 수 있다. "내 식품만"은 API 가 user_id 조건으로 지킨다 (D-061).

비밀번호는 .env 에서만 읽는다 (Git 과 채팅에 쓰지 않는다).
  APP_DB_USER      만들 앱 계정 이름
  APP_DB_PASSWORD  그 계정의 비밀번호
여러 번 실행해도 같은 결과다 (이미 있으면 비밀번호와 권한만 다시 맞춘다).

사용: backend 폴더에서  python -m app.db.setup_roles   (DATABASE_ADMIN_URL 로 연결)
수파베이스에서는 계정 이름 규칙(연결 문자열의 사용자 이름) 때문에 연결 문자열 쪽 확인이 필요할 수 있다.
BYPASSRLS 를 줄 권한이 개발자 계정에 없으면 InsufficientPrivilege 로 멈춘다 (아무것도 바뀌지 않는다).
"""
import psycopg
from psycopg import sql

from app.db.connection import connect_admin, env_value

READ_WRITE = ("users", "sessions", "foods", "legacy_migration", "photo_analyses")
READ_ADD = ("rules", "rule_storage", "daily_tips")  # 읽기 + 더하기 (Q-27, 오늘의 일반 조언은 하루 한 줄을 더한다)
READ_ONLY = ("rule_aliases",)


def setup_app_role(conn: psycopg.Connection, user: str, password: str, schema: str = "public") -> None:
    """앱 계정을 만들거나 맞추고 권한을 준다. commit 은 부르는 쪽."""
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,)).fetchone()
    verb = "ALTER" if exists else "CREATE"
    conn.execute(
        sql.SQL(verb + " ROLE {} LOGIN PASSWORD {} BYPASSRLS").format(
            sql.Identifier(user), sql.Literal(password)
        )
    )
    role, sch = sql.Identifier(user), sql.Identifier(schema)
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sch, role))
    conn.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}").format(sch, role))
    grants = (
        (READ_WRITE, "SELECT, INSERT, UPDATE, DELETE"),
        (READ_ADD, "SELECT, INSERT"),
        (READ_ONLY, "SELECT"),
    )
    for tables, privileges in grants:
        for table in tables:
            conn.execute(
                sql.SQL("GRANT " + privileges + " ON {}.{} TO {}").format(
                    sch, sql.Identifier(table), role
                )
            )


def main() -> None:
    user = env_value("APP_DB_USER")
    password = env_value("APP_DB_PASSWORD")
    conn = connect_admin()
    try:
        setup_app_role(conn, user, password)
        conn.commit()
    finally:
        conn.close()
    print(f"앱 계정 {user}: 규칙표는 읽기와 더하기(별칭은 읽기만), 나머지 표는 읽기·쓰기, RLS 건너뛰기")


if __name__ == "__main__":
    main()
