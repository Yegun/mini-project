"""수파베이스의 REST API 로 우리 표가 열리지 않게 권한 회수

Revision ID: 0002
Revises: 0001

수파베이스는 public 표를 anon·authenticated 역할로 REST API 에 열 수 있다. 우리 서버는 DB 에 직접 연결하므로
이 두 역할에는 권한이 필요 없다. 비밀번호 해시가 든 users 표를 포함해 모든 표의 권한을 회수한다.
이 역할이 없는 DB(내 컴퓨터 PostgreSQL)에서는 아무것도 하지 않는다.
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

API_ROLES = ("anon", "authenticated")

# % 와 : 를 쓰지 않는다 (DB 드라이버가 자리 표시로 읽지 않게)
UP = f"""
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY[{", ".join(f"'{role}'" for role in API_ROLES)}] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA ' || quote_ident(current_schema())
                || ' FROM ' || quote_ident(api_role);
            EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA ' || quote_ident(current_schema())
                || ' REVOKE ALL ON TABLES FROM ' || quote_ident(api_role);
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    # 회수한 권한을 다시 열어 주지 않는다. 열려 있던 상태로 돌아가는 것은 안전하지 않다.
    pass
