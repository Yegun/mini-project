import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))  # backend/ 를 import 경로에

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.main import app as fridge_api  # 지금의 API 앱 그대로

app = FastAPI(lifespan=fridge_api.router.lifespan_context)  # 안쪽 앱의 시작 절차를 넘긴다
app.mount("/api", fridge_api)  # /api/… → API 앱의 /…
app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True))  # 그 밖 → 화면 (반드시 /api 보다 아래)
