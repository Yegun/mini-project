"""규칙표 창구. 규칙표는 읽기만 한다 (D-007)."""
from fastapi import APIRouter

from app.database import transaction
from app.db import rules_repo
from app.routers.common import Conn, UserId
from app.services import disallowed_storages

router = APIRouter()


@router.get("/rules")
def search_rules(conn: Conn, user_id: UserId, q: str = ""):
    """C1 규칙표 검색 🔒. 이름이나 별칭에 검색어가 들어 있으면 찾는다. 오타 보정은 없다.

    검색어가 비어 있거나 찾는 것이 없으면 오류가 아니라 빈 목록이다 (D-035). 모든 계정이 같은 규칙표를 읽는다 (D-062).
    """
    with transaction(conn):
        found = rules_repo.search_rules(conn, q)
    return {
        "items": [
            {
                "name": rule["name"],
                "default_storage": rule["default_storage"],
                "disallowed_storages": disallowed_storages(rule),
                "category": rule["category"],
            }
            for rule in found
        ]
    }
