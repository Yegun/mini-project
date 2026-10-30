"""규칙표 창구. 규칙표는 읽기만 한다 (D-007)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from app import repo_rules
from app.database import get_rules_conn, transaction
from app.validation import ValidationError

router = APIRouter()

RulesConn = Annotated[sqlite3.Connection, Depends(get_rules_conn)]


@router.get("/rules")
def search_rules(q: str, rules_conn: RulesConn):
    """A2 규칙표 검색. 이름이나 별칭에 검색어가 들어 있으면 찾는다. 오타 보정은 없다."""
    word = q.strip().casefold()
    if word == "":
        raise ValidationError("q", "required")
    with transaction(rules_conn, "load_failed"):
        rules = repo_rules.list_rules(rules_conn)
    found = [
        rule
        for rule in rules
        if word in rule["name"].casefold()
        or any(word in alias.casefold() for alias in rule["aliases"])
    ]
    return {
        "rules": [
            {
                "name": rule["name"],
                "aliases": rule["aliases"],
                "default_storage": rule["default_storage"],
                "not_allowed": repo_rules.not_allowed_storages(rule),
            }
            for rule in found
        ]
    }
