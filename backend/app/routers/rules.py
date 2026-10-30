"""규칙표 창구. 규칙표는 읽기만 한다 (D-007)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from app.database import get_rules_conn, transaction
from app.db import rules_repo
from app.services import not_allowed_storages

router = APIRouter()

RulesConn = Annotated[sqlite3.Connection, Depends(get_rules_conn)]


@router.get("/rules")
def search_rules(rules_conn: RulesConn, q: str = ""):
    """A2 규칙표 검색. 이름이나 별칭에 검색어가 들어 있으면 찾는다. 오타 보정은 없다.

    검색어가 비어 있으면 오류가 아니라 빈 목록이다 (D-035, API-SPEC A2).
    """
    with transaction(rules_conn, "load_failed"):
        found = rules_repo.search_rules(rules_conn, q)
    return {
        "rules": [
            {
                "name": rule["name"],
                "default_storage": rule["default_storage"],
                "not_allowed": not_allowed_storages(rule),
            }
            for rule in found
        ]
    }
