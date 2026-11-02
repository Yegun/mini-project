"""알렘빅 실행 환경. 접속 정보는 .env 의 DATABASE_ADMIN_URL (개발자 계정)에서 읽는다.

표는 SQL 로 직접 쓰므로 표 모양 자동 비교(autogenerate)는 쓰지 않는다 (target_metadata 없음).
버전 파일 하나가 한 묶음이다. 중간에 실패하면 그 파일은 아무것도 바뀌지 않는다.

시험은 app/db/migrate.py 가 config.attributes 로 주소(url)와 임시 schema(schema)를 넘겨 이 파일을 지난다.
"""
from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

from app.db.connection import env_value

config = context.config


def _engine():
    url = make_url(config.attributes.get("url") or env_value("DATABASE_ADMIN_URL"))
    # 우리는 psycopg 3 를 쓴다. prepare_threshold=None 은 수파베이스 연결 풀러에서도 동작하게 하려는 설정이다.
    connect_args = {"prepare_threshold": None}
    schema = config.attributes.get("schema")
    if schema:
        connect_args["options"] = f"-c search_path={schema}"
    return create_engine(
        url.set(drivername="postgresql+psycopg"), poolclass=pool.NullPool, connect_args=connect_args
    )


def run_migrations_online() -> None:
    engine = _engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, transaction_per_migration=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations_online()
