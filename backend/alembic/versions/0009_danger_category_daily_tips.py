"""위험 식품·식품 종류 칸과 오늘의 일반 조언 표 daily_tips 만들기 (v0.5.0)

Revision ID: 0009
Revises: 0008

1) 규칙표 rules 에 칸 세 개 (DATA-MODEL 5-1, D-164, D-167)
   - is_danger: 위험 식품인지. 기본 거짓
   - danger_note: 위험 이유 한 줄. 위험이 아니면 비운다
   - category: 식품 종류 (vegetable / fruit / meat / seafood / other)
   이미 들어 있는 처음 30개는 종류를 채우고, 수산 4개와 육류 3개를 위험 식품으로 정한다 (DATA-MODEL 5-3, 5-4).
   사진 등록으로 먼저 더해진 식품은 종류가 other, 위험 아님으로 시작한다 (AI 가 알려 준 값은 이 버전 전에는 저장하지 않았다).
   위험 여부와 이유의 짝, 종류 값은 DB 가 막지 않는다. 규칙표 채우기와 API 가 지킨다 (Q-36).

2) 식품 foods 에 칸 하나 (DATA-MODEL 2절, D-164)
   - category: 직접 등록 식품만 값이 있다. 규칙표 식품은 규칙표 값을 읽어 붙이므로 비워 둔다.
   이미 있는 직접 등록 식품은 종류를 고른 적이 없으므로 other 로 채운다.
   DB 규칙: 비어 있거나 다섯 값 중 하나, 직접 등록 식품(source = manual)은 비어 있지 않음 (Q-08).

3) 오늘의 일반 조언 daily_tips (DATA-MODEL 6-1, Q-37)
   한국 시간 하루에 한 줄, 모든 계정이 같은 줄을 읽는다. 주인(계정) 칸이 없다.
   수파베이스 REST API 역할(anon·authenticated)에는 권한을 주지 않고 RLS 를 켠다 (표 9개 모두, Q-33).
   앱 계정의 권한(읽기와 더하기)은 python -m app.db.setup_roles 가 준다.

이 파일 안의 값은 seed_rules.py 와 같아야 한다 (시험이 맞는지 확인한다). 이미 적용한 파일은 고치지 않는다.
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

API_ROLES = ("anon", "authenticated")
CATEGORIES = ("vegetable", "fruit", "meat", "seafood", "other")

# 처음 30개의 종류 (DATA-MODEL 5-3)
CATEGORY_OF = {
    **dict.fromkeys(
        ("양파", "대파", "감자", "당근", "양배추", "오이", "상추", "시금치", "마늘", "애호박", "토마토", "배추", "버섯"),
        "vegetable",
    ),
    **dict.fromkeys(("사과", "바나나", "딸기", "귤", "포도", "배"), "fruit"),
    **dict.fromkeys(("돼지고기", "소고기", "닭고기"), "meat"),
    **dict.fromkeys(("고등어", "오징어", "새우", "연어"), "seafood"),
    **dict.fromkeys(("달걀", "우유", "두부", "콩나물"), "other"),
}

# 위험 식품 7개와 이유 한 줄 (DATA-MODEL 5-4)
DANGER_NOTE_OF = {
    "고등어": "고등어는 쉽게 상하고, 상한 것을 먹으면 두드러기와 구토가 생길 수 있어요",
    "오징어": "오징어는 날것이나 덜 익힌 것을 먹으면 식중독이 생기기 쉬워요",
    "새우": "새우는 쉽게 상하고, 날것이나 덜 익힌 것을 먹으면 식중독이 생길 수 있어요",
    "연어": "연어는 날것으로 먹으면 기생충이 있을 수 있어요",
    "돼지고기": "돼지고기는 덜 익혀 먹으면 기생충과 식중독의 위험이 있어요",
    "소고기": "소고기는 덜 익혀 먹으면 식중독 균이 남아 있을 수 있어요",
    "닭고기": "닭고기는 덜 익혀 먹으면 살모넬라 같은 식중독의 위험이 있어요",
}

CATEGORY_CHECK = "category IN (" + ", ".join(f"'{c}'" for c in CATEGORIES) + ")"

CREATE_DAILY_TIPS = """
CREATE TABLE daily_tips (
    tip_date date PRIMARY KEY,
    tips     jsonb NOT NULL CHECK (jsonb_typeof(tips) = 'array' AND jsonb_array_length(tips) > 0)
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
            EXECUTE 'REVOKE ALL ON daily_tips FROM ' || quote_ident(api_role);
        END IF;
    END LOOP;
END
$$
"""


def _quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def upgrade() -> None:
    # 1) 규칙표
    op.execute("ALTER TABLE rules ADD COLUMN is_danger boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE rules ADD COLUMN danger_note text")
    op.execute("ALTER TABLE rules ADD COLUMN category text NOT NULL DEFAULT 'other'")
    for name, category in CATEGORY_OF.items():
        op.execute(f"UPDATE rules SET category = {_quote(category)} WHERE name = {_quote(name)}")
    for name, note in DANGER_NOTE_OF.items():
        op.execute(
            f"UPDATE rules SET is_danger = true, danger_note = {_quote(note)} WHERE name = {_quote(name)}"
        )
    # 칸을 채우는 쪽이 값을 꼭 정하게 기본값은 없앤다 (is_danger 는 거짓이 기본이라 둔다)
    op.execute("ALTER TABLE rules ALTER COLUMN category DROP DEFAULT")

    # 2) 식품
    op.execute("ALTER TABLE foods ADD COLUMN category text")
    op.execute("UPDATE foods SET category = 'other' WHERE source = 'manual'")
    op.execute(
        "ALTER TABLE foods ADD CONSTRAINT foods_category_check CHECK ("
        f"(category IS NULL OR {CATEGORY_CHECK}) AND (source <> 'manual' OR category IS NOT NULL))"
    )

    # 3) 오늘의 일반 조언
    op.execute(CREATE_DAILY_TIPS)
    op.get_bind().exec_driver_sql(REVOKE)
    op.execute("ALTER TABLE daily_tips ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP TABLE daily_tips")
    op.execute("ALTER TABLE foods DROP CONSTRAINT foods_category_check")
    op.execute("ALTER TABLE foods DROP COLUMN category")
    op.execute("ALTER TABLE rules DROP COLUMN category")
    op.execute("ALTER TABLE rules DROP COLUMN danger_note")
    op.execute("ALTER TABLE rules DROP COLUMN is_danger")
