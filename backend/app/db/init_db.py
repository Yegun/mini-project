"""DB 를 만들고 규칙표를 채운다. 여러 번 실행해도 같은 결과다 (식품 데이터는 건드리지 않는다).

사용: backend 폴더에서  python -m app.db.init_db
"""
from app.db.connection import connect_foods, connect_rules, foods_db_path, rules_db_path
from app.db.schema import create_foods_schema, create_rules_schema
from app.db.seed_rules import seed_rules


def _create_foods(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    foods = connect_foods(path)
    try:
        create_foods_schema(foods)
    finally:
        foods.close()


def _create_rules(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rules = connect_rules(path, readonly=False)
    try:
        create_rules_schema(rules)
        seed_rules(rules)
    finally:
        rules.close()


def init_db() -> None:
    foods_path, rules_path = foods_db_path(), rules_db_path()
    _create_foods(foods_path)
    _create_rules(rules_path)

    print(f"식품 DB: {foods_path}")
    print(f"규칙표 DB: {rules_path}")


def ensure_db() -> None:
    """서버가 켜질 때 부른다. 없는 DB 파일만 만든다.

    init_db 는 규칙표를 지우고 다시 채우므로, 이미 있는 파일은 건드리지 않는다
    (식품 데이터와 개발자가 고친 규칙표를 지키기 위해서다, D-007).
    """
    foods_path, rules_path = foods_db_path(), rules_db_path()
    if not foods_path.exists():
        _create_foods(foods_path)
    if not rules_path.exists():
        _create_rules(rules_path)


if __name__ == "__main__":
    init_db()
