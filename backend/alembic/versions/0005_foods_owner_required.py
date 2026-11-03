"""식품의 주인 칸을 비울 수 없게 바꾸기 (NOT NULL + 외래키)

Revision ID: 0005
Revises: 0004

0004 까지 모든 식품에 주인이 붙었다. 이제 주인 없는 식품은 있을 수 없다 (D-061).
주인이 없는 행이 하나라도 남아 있으면 이 단계가 실패하고 아무것도 바뀌지 않는다. 앞 단계가 끝났는지 확인하는 역할도 한다.
계정이 지워지면 그 계정의 식품도 따라 지운다 (DATA-MODEL Q-09).
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE foods ALTER COLUMN user_id SET NOT NULL")
    op.execute(
        "ALTER TABLE foods ADD CONSTRAINT foods_user_id_fkey"
        " FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE foods DROP CONSTRAINT foods_user_id_fkey")
    op.execute("ALTER TABLE foods ALTER COLUMN user_id DROP NOT NULL")
