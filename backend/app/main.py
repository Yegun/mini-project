from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import foods, rules

app = FastAPI(title="task-flow API")
register_error_handlers(app)
app.include_router(foods.router)
app.include_router(rules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
