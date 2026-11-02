"""기존 식품 옮김 기록 표 legacy_migration 만들기

Revision ID: 0007
Revises: 0006

"첫 계정이 누구이고, 기존 식품을 이미 넘겨받았는지"를 적어 두는 표다 (DATA-MODEL 7-1, D-097).
옮기다 실패해도 계정은 남고, 첫 계정이 다음에 로그인할 때 성공할 때까지 다시 시도하려면 첫 계정을 기억해야 한다.
- id: 항상 1. 줄이 한 개뿐이다(두 사람이 동시에 처음 가입해도 한 줄만 생긴다).
- user_id: 옮겨 받는 계정(첫 계정). 그 계정이 지워지면 이 칸만 비워지고 줄은 남는다.
- migrated: 옮김이 끝났는지.
이미 실제 가입자가 있는 DB 는 옛 가입 방식이 가입과 함께 식품을 넘겼으므로 "옮김 끝"으로 적어 둔다.
이전용 계정이 아직 식품을 맡고 있으면 줄을 만들지 않는다(다음 첫 가입이 첫 계정이 된다).
수파베이스 REST API 역할(anon·authenticated)에는 이 표의 권한도 주지 않는다 (0006 과 같은 이유). 그 역할이 없는 DB 에서는 건너뛴다.
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

LEGACY_EMAIL = "legacy@fridge.invalid"
API_ROLES = ("anon", "authenticated")

# % 와 : 를 쓰지 않는다 (DB 드라이버가 자리 표시로 읽지 않게)
REVOKE = f"""
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY[{", ".join(f"'{role}'" for role in API_ROLES)}] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE 'REVOKE ALL ON legacy_migration FROM ' || quote_ident(api_role);
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    op.execute(
        "CREATE TABLE legacy_migration ("
        " id integer PRIMARY KEY CHECK (id = 1),"
        " user_id uuid REFERENCES users (id) ON DELETE SET NULL,"
        " migrated boolean NOT NULL DEFAULT false)"
    )
    op.execute(
        "INSERT INTO legacy_migration (id, user_id, migrated)"
        " SELECT 1, NULL, true"
        f" WHERE EXISTS (SELECT 1 FROM users WHERE email <> '{LEGACY_EMAIL}')"
        f" AND NOT EXISTS (SELECT 1 FROM foods WHERE user_id = (SELECT id FROM users WHERE email = '{LEGACY_EMAIL}'))"
    )
    op.get_bind().exec_driver_sql(REVOKE)


def downgrade() -> None:
    op.execute("DROP TABLE legacy_migration")
