"""새 DB 구조 만들기: 계정·로그인 상태·식품·규칙표 (DATA-MODEL.md 1절 ~ 5절)

Revision ID: 0001
Revises:

단계적 이전의 첫 단계다. 식품의 주인 칸(foods.user_id)은 **비울 수 있게** 만든다.
기존 식품에 주인을 붙이는 일이 끝난 뒤(0004) 0005 에서 비울 수 없게 하고 외래키를 건다.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# 표 정의는 SQL 로 직접 쓴다. 여기서 % 와 : 를 쓰지 않으므로 그대로 DB 에 보낸다.
UP = """
-- 날짜는 DATE(시각 없음, Q-01), 번호는 UUID(Q-04), 허용 값은 글자 + CHECK(Q-07).
-- 여유·주의·임박·지남, 기록 숫자는 저장하지 않는다 (D-011). 오늘 날짜는 DB 시계가 아니라 API 가 넘긴다 (D-088).

-- 4-1. 계정. 이메일은 앞뒤 공백 없이 소문자로 저장한다 (Q-02, Q-06).
CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         text NOT NULL UNIQUE
                  CHECK (length(email) > 0 AND email = lower(btrim(email))),
    password_hash text NOT NULL CHECK (length(password_hash) > 0)  -- 솔트는 이 값 안에 들어 있다 (D-094, Q-11)
);

-- 4-2. 로그인 상태. 기기 한 대 = 한 줄. id 는 쿠키 값의 해시다 (Q-12). 시각은 DB 시계 (Q-13).
CREATE TABLE sessions (
    id           text PRIMARY KEY CHECK (length(id) > 0),
    user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    last_used_at timestamptz NOT NULL DEFAULT now()
);

-- 2절. 식품. 만든 시각·고친 시각 칸은 없다 (D-028).
-- user_id(주인)는 처음에는 비울 수 있다. 0004 에서 모든 식품에 주인을 붙이고, 0005 에서 NOT NULL + 외래키를 건다.
CREATE TABLE foods (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        uuid,
    name           text NOT NULL CHECK (length(btrim(name)) > 0),
    storage        text NOT NULL CHECK (storage IN ('room', 'fridge', 'freezer')),
    quantity       numeric(10, 2) NOT NULL CHECK (quantity > 0),
    unit           text NOT NULL CHECK (length(btrim(unit)) > 0),
    purchase_date  date NOT NULL,
    expiry_date    date NOT NULL,
    source         text NOT NULL CHECK (source IN ('rule', 'manual')),
    status         text NOT NULL DEFAULT 'none' CHECK (status IN ('none', 'eaten', 'discarded')),
    processed_date date,
    CHECK (purchase_date <= expiry_date),
    -- 처리 상태가 none 이면 처리한 날짜는 비어 있고, 아니면 채워져 있다 (Q-08)
    CHECK ((status = 'none' AND processed_date IS NULL)
        OR (status <> 'none' AND processed_date IS NOT NULL))
);

-- 색인 두 개 (Q-10): 홈 목록용, 기록 목록용
CREATE INDEX foods_home_idx
    ON foods (user_id, status, expiry_date, purchase_date, name);
CREATE INDEX foods_records_idx
    ON foods (user_id, status, processed_date);

-- 5절. 규칙표 (읽기 전용, 모든 계정 공통). 번호는 이름에서 계산한 값이라 DB 가 만들지 않는다 (Q-04 의 예외).
CREATE TABLE rules (
    id              uuid PRIMARY KEY,
    name            text NOT NULL UNIQUE CHECK (length(btrim(name)) > 0),
    default_storage text NOT NULL CHECK (default_storage IN ('room', 'fridge', 'freezer'))
);

CREATE TABLE rule_aliases (
    rule_id uuid NOT NULL REFERENCES rules (id) ON DELETE CASCADE,
    alias   text NOT NULL UNIQUE CHECK (length(btrim(alias)) > 0),
    PRIMARY KEY (rule_id, alias)
);

CREATE TABLE rule_storage (
    rule_id  uuid NOT NULL REFERENCES rules (id) ON DELETE CASCADE,
    storage  text NOT NULL CHECK (storage IN ('room', 'fridge', 'freezer')),
    allowed  boolean NOT NULL,
    max_days integer,
    PRIMARY KEY (rule_id, storage),
    -- 가능이면 최대 보관 일수가 0보다 크고, 불가면 비운다 (DATA-MODEL 5-3)
    CHECK ((allowed AND max_days IS NOT NULL AND max_days > 0)
        OR (NOT allowed AND max_days IS NULL))
);
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    # 만든 순서의 거꾸로. 별칭·보관 방법별 정보가 규칙표 식품을, 로그인 상태가 계정을 가리킨다.
    for table in ("rule_storage", "rule_aliases", "rules", "foods", "sessions", "users"):
        op.execute(f"DROP TABLE {table}")
