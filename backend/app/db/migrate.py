"""표를 만들고 바꾼다. 알렘빅(Alembic)으로 버전을 관리한다 (alembic/versions 의 파일을 번호 순서대로 한 번씩).

DB 가 "어느 버전까지 적용됐는지"는 DB 안의 alembic_version 표에 기록된다. 여러 번 실행해도 이미 한 것은 건너뛴다.
버전 파일 하나는 한 묶음이다. 중간에 실패하면 그 파일은 아무것도 바뀌지 않는다.
알렘빅 명령을 직접 써도 된다 (backend 폴더에서 alembic upgrade head, alembic downgrade -1, alembic history, alembic current).

사용: backend 폴더에서  python -m app.db.migrate         최신까지 올린다 (DATABASE_ADMIN_URL 로 연결)
                         python -m app.db.migrate down    한 단계 되돌린다
"""
import sys

from alembic import command
from alembic.config import Config

from app.db.connection import BACKEND_DIR


def alembic_config(url: str | None = None, schema: str | None = None) -> Config:
    """url, schema 는 시험이 임시 schema 에 올릴 때만 준다. 없으면 .env 의 DATABASE_ADMIN_URL 을 쓴다."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    if url:
        config.attributes["url"] = url
    if schema:
        config.attributes["schema"] = schema
    return config


def upgrade(url: str | None = None, schema: str | None = None, revision: str = "head") -> None:
    command.upgrade(alembic_config(url, schema), revision)


def downgrade(url: str | None = None, schema: str | None = None, revision: str = "-1") -> None:
    command.downgrade(alembic_config(url, schema), revision)


def main(argv: list[str]) -> int:
    if argv and argv[0] == "down":
        downgrade()
        print("한 단계 되돌렸다.")
    elif not argv:
        upgrade()
        print("최신 버전까지 적용했다.")
    else:
        print("사용: python -m app.db.migrate [down]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
