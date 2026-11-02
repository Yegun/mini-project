"""PostgreSQL 연결 (D-038, D-041). 연결 문자열은 .env 에만 둔다 (AGENTS.md, TEAM 조 규칙 3).

.env 항목 (값은 Git 에 올리지 않는다)
  DATABASE_URL        앱(API)이 쓰는 DB 계정. 규칙표 세 표는 읽기만 된다 (Q-16)
  DATABASE_ADMIN_URL  개발자 작업용 DB 계정. 표 만들기·규칙표 채우기·기한 다시 계산에만 쓴다
  TEST_DATABASE_URL   시험용 DB (시험이 임시 schema 를 만들고 지운다)

연결은 자동 저장(autocommit)이 아니다. 저장소 함수는 commit 을 하지 않고, 부르는 쪽이 한 요청 = 한 묶음으로
commit / rollback 한다 (API-SPEC 0절 "요청 단위").

옛 SQLite 파일(v0.2.0) 위치는 기존 식품을 옮길 때만 쓴다 (D-038, D-098).
"""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"


class DatabaseConfigError(RuntimeError):
    """연결 문자열이 .env 에도 환경 변수에도 없다."""


def _load_env_files() -> None:
    """프로젝트 폴더와 backend 폴더의 .env 를 읽는다. 이미 있는 환경 변수는 덮어쓰지 않는다."""
    for env_file in (PROJECT_DIR / ".env", BACKEND_DIR / ".env"):
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_value(name: str) -> str:
    _load_env_files()
    url = os.environ.get(name)
    if not url:
        raise DatabaseConfigError(f".env 에 {name} 가 없다. .env.example 를 참고해 적는다.")
    return url


def _open(url: str, **kwargs) -> psycopg.Connection:
    # prepare_threshold=None: 수파베이스 연결 풀러(트랜잭션 모드)에서도 동작하게 서버 쪽 준비문을 쓰지 않는다.
    return psycopg.connect(url, row_factory=dict_row, prepare_threshold=None, **kwargs)


def connect_app() -> psycopg.Connection:
    """앱(API)용 연결. 식품·계정·로그인 상태는 읽고 쓰고, 규칙표는 읽기만 된다."""
    return _open(env_value("DATABASE_URL"))


def connect_admin() -> psycopg.Connection:
    """개발자 작업용 연결. 앱·API 코드에서는 부르지 않는다 (D-007)."""
    return _open(env_value("DATABASE_ADMIN_URL"))


def connect_test(schema: str) -> psycopg.Connection:
    """시험용 연결. 주어진 schema 만 보이게 연다."""
    return _open(env_value("TEST_DATABASE_URL"), options=f"-c search_path={schema}")


def foods_db_path() -> Path:
    """옛 SQLite 식품 파일. 기존 식품 옮기기의 읽을 곳이다."""
    return Path(os.environ.get("FRIDGE_DB_PATH", DATA_DIR / "fridge.db"))


def rules_db_path() -> Path:
    """옛 SQLite 규칙표 파일. 지금은 쓰지 않는다 (규칙표는 PostgreSQL 에 있다, D-041)."""
    return Path(os.environ.get("RULES_DB_PATH", DATA_DIR / "rules.db"))
