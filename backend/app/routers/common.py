"""창구들이 같이 쓰는 것. 요청 본문의 바탕 모양과 자주 쓰는 의존 값."""
from datetime import date
from typing import Annotated

import psycopg
from fastapi import Depends
from pydantic import BaseModel, ConfigDict

from app.auth import current_user
from app.database import get_conn, get_today

Conn = Annotated[psycopg.Connection, Depends(get_conn)]
Today = Annotated[date, Depends(get_today)]
# 로그인한 계정의 번호. 🔒 창구는 이것을 받아서 "내 식품만" 다룬다 (D-061).
UserId = Annotated[str, Depends(current_user)]


class Body(BaseModel):
    """요청 본문. 값 검사는 validation.py 가 직접 한다 (D-010). 필요 없는 칸이 와도 무시한다 (API-SPEC 5절 9번)."""

    model_config = ConfigDict(extra="ignore")
