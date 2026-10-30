"""DB 를 만들고 규칙표를 채운다. 여러 번 실행해도 같은 결과다 (식품 데이터는 건드리지 않는다).

사용: backend 폴더에서  python -m app.db.init_db
"""
from app.db.connection import connect_foods, connect_rules, foods_db_path, rules_db_path
from app.db.schema import create_foods_schema, create_rules_schema
from app.db.seed_rules import seed_rules


def init_db() -> None:
    foods_path, rules_path = foods_db_path(), rules_db_path()
    foods_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.parent.mkdir(parents=True, exist_ok=True)

    foods = connect_foods(foods_path)
    try:
        create_foods_schema(foods)
    finally:
        foods.close()

    rules = connect_rules(rules_path, readonly=False)
    try:
        create_rules_schema(rules)
        seed_rules(rules)
    finally:
        rules.close()

    print(f"식품 DB: {foods_path}")
    print(f"규칙표 DB: {rules_path}")


if __name__ == "__main__":
    init_db()
