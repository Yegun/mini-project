from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.init_db import ensure_db
from app.errors import register_error_handlers
from app.routers import foods, rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_db()  # DB 파일이 없으면 처음 켤 때 만든다. 있으면 건드리지 않는다.
    yield


app = FastAPI(title="task-flow API", lifespan=lifespan)
register_error_handlers(app)
app.include_router(foods.router)
app.include_router(rules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
