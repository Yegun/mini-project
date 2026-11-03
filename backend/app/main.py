from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import account, auth, foods, recommendations, records, rules

# 표 준비(migrate, init_db)는 개발자가 따로 실행한다. 서버가 켜질 때 표를 만들지 않는다.
app = FastAPI(title="task-flow API")
register_error_handlers(app)
app.include_router(auth.router)
app.include_router(rules.router)
app.include_router(foods.router)
app.include_router(records.router)
app.include_router(account.router)
app.include_router(recommendations.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
