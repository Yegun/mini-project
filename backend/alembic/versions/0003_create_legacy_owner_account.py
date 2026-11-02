"""이전용 계정 만들기. 로그인할 수 없는 계정

Revision ID: 0003
Revises: 0002

옛 식품을 잠시 맡아 둘 계정이다. 처음 가입하는 사람이 생기면 서버가 이 계정의 식품을 그 사람에게 넘긴다 (D-042, D-043).
- 이메일 legacy@fridge.invalid : .invalid 는 실제로 쓸 수 없는 주소 모양이다. 서버 코드의 LEGACY_EMAIL 과 같은 값이다.
- 비밀번호 해시 자리에는 해시가 아닌 값 '!' 를 둔다. 어떤 비밀번호도 맞지 않아서 로그인할 수 없다.
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

LEGACY_EMAIL = "legacy@fridge.invalid"


def upgrade() -> None:
    op.execute(
        f"INSERT INTO users (email, password_hash) VALUES ('{LEGACY_EMAIL}', '!') ON CONFLICT (email) DO NOTHING"
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM users WHERE email = '{LEGACY_EMAIL}'")
