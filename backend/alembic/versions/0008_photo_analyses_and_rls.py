"""사진 읽기 결과 표 photo_analyses 만들기 + 표 8개에 RLS 켜기

Revision ID: 0008
Revises: 0007

1) photo_analyses (DATA-MODEL 6절, Q-28 ~ Q-31): 사진 한 장을 읽은 결과(글만)를 계정마다 한 줄, 30분 동안 잠깐 보관한다.
   한꺼번에 등록할 때 규칙표에 더하는 값을 서버가 가진 AI 결과에서만 가져오게 하려는 것이다 (D-133, D-136).
   - id: 사진 읽기 응답의 analysis_id (DB 가 만든다)
   - user_id: 이 결과를 만든 계정. 계정마다 한 줄이라 중복 불가이고, 계정이 지워지면 따라 지워진다 (Q-09, Q-29)
   - items: 읽은 식품 목록(JSONB). 사진도 영수증에 적힌 글 전체도 담지 않는다 (D-102)
   - created_at: DB 시계. 30분이 지나면 쓸 수 없다 (Q-13, Q-31)
   수파베이스 REST API 역할(anon·authenticated)에는 이 표의 권한도 주지 않는다 (0006, 0007 과 같은 이유).

2) 표 8개 모두 RLS(줄 단위 보안)를 켠다. 정책은 만들지 않는다 (Q-33).
   RLS 를 거치는 역할(anon, authenticated)은 어떤 줄도 볼 수 없다. 앱 DB 계정은 RLS 를 건너뛰는 속성(BYPASSRLS)을 가져야
   읽고 쓸 수 있다 (python -m app.db.setup_roles 가 준다). "내 식품만"은 API 가 user_id 조건으로 지킨다 (D-061).
   표를 만든 계정(표 주인)과 superuser 는 RLS 를 건너뛰므로 개발자 계정과 시험은 영향이 없다.
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

API_ROLES = ("anon", "authenticated")
OLD_TABLES = ("users", "sessions", "foods", "rules", "rule_aliases", "rule_storage", "legacy_migration")
ALL_TABLES = OLD_TABLES + ("photo_analyses",)

CREATE = """
CREATE TABLE photo_analyses (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
    items      jsonb NOT NULL CHECK (jsonb_typeof(items) = 'array'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
)
"""

# % 와 : 를 쓰지 않는다 (DB 드라이버가 자리 표시로 읽지 않게)
REVOKE = f"""
DO $$
DECLARE
    api_role text;
BEGIN
    FOREACH api_role IN ARRAY ARRAY[{", ".join(f"'{role}'" for role in API_ROLES)}] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE 'REVOKE ALL ON photo_analyses FROM ' || quote_ident(api_role);
        END IF;
    END LOOP;
END
$$
"""


def upgrade() -> None:
    op.execute(CREATE)
    op.get_bind().exec_driver_sql(REVOKE)
    for table in ALL_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in OLD_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE photo_analyses")
