"""주인 없는 식품을 모두 이전용 계정에 넘기기

Revision ID: 0004
Revises: 0003

0002 에서 가져온 식품은 주인이 없다. 모두 이전용 계정(0003)의 것으로 한다.
이 일이 끝나야 0005 에서 주인 칸을 비울 수 없게 바꿀 수 있다.
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

LEGACY_EMAIL = "legacy@fridge.invalid"


def upgrade() -> None:
    op.execute(
        "UPDATE foods SET user_id = (SELECT id FROM users WHERE email = '%s') WHERE user_id IS NULL"
        % LEGACY_EMAIL
    )


def downgrade() -> None:
    # 이전용 계정이 아직 갖고 있는 식품만 다시 주인 없는 상태로 되돌린다.
    # 첫 가입자에게 이미 넘어간 식품은 건드리지 않는다(누구에게서 왔는지 기록이 없어 되돌릴 수 없다).
    op.execute(
        "UPDATE foods SET user_id = NULL WHERE user_id = (SELECT id FROM users WHERE email = '%s')"
        % LEGACY_EMAIL
    )
