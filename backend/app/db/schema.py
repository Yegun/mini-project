"""표 만드는 문장. 칸 이름·값·자료형은 DATA-MODEL.md 와 D-032 를 따른다.

날짜는 `YYYY-MM-DD` 글자(시각 없음, D-031). 여유·주의·임박·지남은 저장하지 않는다 (D-011).
"""
import sqlite3

# date(x) IS x : 'YYYY-MM-DD' 모양의 올바른 날짜일 때만 참이 된다.
FOODS_SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id            TEXT PRIMARY KEY CHECK (length(id) = 36),
    name          TEXT NOT NULL CHECK (length(trim(name)) > 0),
    storage       TEXT NOT NULL CHECK (storage IN ('room', 'fridge', 'freezer')),
    quantity      REAL NOT NULL CHECK (typeof(quantity) IN ('real', 'integer') AND quantity > 0),
    unit          TEXT NOT NULL CHECK (length(trim(unit)) > 0),
    purchase_date TEXT NOT NULL CHECK (date(purchase_date) IS purchase_date),
    expiry_date   TEXT NOT NULL CHECK (date(expiry_date) IS expiry_date),
    source        TEXT NOT NULL CHECK (source IN ('rule', 'manual')),
    status        TEXT NOT NULL DEFAULT 'none' CHECK (status IN ('none', 'eaten', 'discarded')),
    CHECK (purchase_date <= expiry_date)
);
CREATE INDEX IF NOT EXISTS idx_foods_list
    ON foods (status, expiry_date, purchase_date, name);
"""

RULES_SCHEMA = """
CREATE TABLE IF NOT EXISTS rules (
    id              TEXT PRIMARY KEY CHECK (length(id) = 36),
    name            TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    default_storage TEXT NOT NULL CHECK (default_storage IN ('room', 'fridge', 'freezer'))
);

CREATE TABLE IF NOT EXISTS rule_aliases (
    rule_id TEXT NOT NULL REFERENCES rules (id) ON DELETE CASCADE,
    alias   TEXT NOT NULL UNIQUE CHECK (length(trim(alias)) > 0),
    PRIMARY KEY (rule_id, alias)
);

CREATE TABLE IF NOT EXISTS rule_storage (
    rule_id  TEXT NOT NULL REFERENCES rules (id) ON DELETE CASCADE,
    storage  TEXT NOT NULL CHECK (storage IN ('room', 'fridge', 'freezer')),
    allowed  INTEGER NOT NULL CHECK (allowed IN (0, 1)),
    max_days INTEGER,
    PRIMARY KEY (rule_id, storage),
    -- 가능이면 최대 보관 일수가 있어야 하고, 불가면 비운다 (DATA-MODEL 4-3)
    CHECK ((allowed = 1 AND max_days IS NOT NULL AND max_days > 0)
        OR (allowed = 0 AND max_days IS NULL))
);
"""


def create_foods_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(FOODS_SCHEMA)


def create_rules_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(RULES_SCHEMA)
