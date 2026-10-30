"""DB 파일 위치와 연결.

파일은 두 개다 (D-007): 식품 DB(fridge.db), 규칙표 DB(rules.db).
위치는 환경 변수로 바꿀 수 있다. 없으면 backend/data/ 아래에 둔다.
"""
import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def foods_db_path() -> Path:
    return Path(os.environ.get("FRIDGE_DB_PATH", DATA_DIR / "fridge.db"))


def rules_db_path() -> Path:
    return Path(os.environ.get("RULES_DB_PATH", DATA_DIR / "rules.db"))


def _open(target: str, uri: bool) -> sqlite3.Connection:
    conn = sqlite3.connect(target, uri=uri)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_foods(path: Path | str | None = None) -> sqlite3.Connection:
    """식품 DB 에 연결한다 (읽기·쓰기)."""
    return _open(str(path or foods_db_path()), uri=False)


def connect_rules(path: Path | str | None = None, *, readonly: bool = True) -> sqlite3.Connection:
    """규칙표 DB 에 연결한다. 앱·API 는 읽기만 하므로 기본은 읽기 전용이다 (D-007).

    readonly=False 는 규칙표를 만들고 채우는 개발자 작업(init_db)에서만 쓴다.
    """
    target = Path(path or rules_db_path())
    if readonly:
        return _open(f"{target.resolve().as_uri()}?mode=ro", uri=True)
    return _open(str(target), uri=False)
