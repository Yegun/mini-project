"""규칙표 값을 고친 뒤 한 번 돌리는 개발자 작업. 등록된 규칙표 식품의 기한을 다시 계산해 저장한다.

DATA-MODEL 4절을 따른다.
- 대상: source = rule, status = none 인 식품. 직접 등록(manual)과 처리된 식품은 건드리지 않는다.
- 새 기한 = 구매일 + 지금 보관 방법의 새 max_days (A3 계산식). 상태 색은 저장하지 않으므로 따로 할 일이 없다.
- 규칙표 DB 는 읽기만 한다 (D-007). 앱·API 에서는 부르지 않는다.
- 한 번에 성공하거나, 실패하면 아무것도 바뀌지 않는다 (API-SPEC 3절).

문서에 처리 방법이 없는 식품은 계산하지 않고 건너뛴 뒤 알려 준다.
- 이름이 규칙표에 없다
- 지금 보관 방법이 규칙표에서 "불가"가 됐다

사용: backend 폴더에서  python -m app.db.recalc_expiry [--dry-run]
  --dry-run  저장하지 않고 바뀔 내용만 보여 준다
"""
import argparse
import sqlite3
import sys
from datetime import date

from app.calc import expiry_from_days
from app.db.connection import connect_foods, connect_rules, foods_db_path, rules_db_path
from app.db.rules_repo import get_rule_by_name

_TARGETS = (
    "SELECT id, name, storage, purchase_date, expiry_date FROM foods"
    " WHERE source = 'rule' AND status = 'none' ORDER BY purchase_date, name, id"
)
_UPDATE = "UPDATE foods SET expiry_date = ? WHERE id = ? AND source = 'rule' AND status = 'none'"


def recalc_expiry(foods: sqlite3.Connection, rules: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    """결과: {"changed": [(이름, 구매일, 옛 기한, 새 기한)], "same": 개수, "skipped": [(이름, 구매일, 이유)]}"""
    changed, skipped, updates, same = [], [], [], 0
    for row in foods.execute(_TARGETS).fetchall():
        rule = get_rule_by_name(rules, row["name"])
        if rule is None:
            skipped.append((row["name"], row["purchase_date"], "규칙표에 없는 이름"))
            continue
        info = next((s for s in rule["storages"] if s["storage"] == row["storage"]), None)
        if info is None or not info["allowed"]:
            skipped.append((row["name"], row["purchase_date"], "지금 보관 방법이 규칙표에서 불가"))
            continue
        new_expiry = expiry_from_days(date.fromisoformat(row["purchase_date"]), info["max_days"]).isoformat()
        if new_expiry == row["expiry_date"]:
            same += 1
            continue
        changed.append((row["name"], row["purchase_date"], row["expiry_date"], new_expiry))
        updates.append((new_expiry, row["id"]))
    if updates and not dry_run:
        with foods:  # 하나라도 실패하면 모두 되돌린다
            foods.executemany(_UPDATE, updates)
    return {"changed": changed, "same": same, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="규칙표 식품의 기한을 규칙표 값으로 다시 계산한다.")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 바뀔 내용만 보여 준다")
    args = parser.parse_args(argv)

    for label, path in (("식품 DB", foods_db_path()), ("규칙표 DB", rules_db_path())):
        if not path.exists():
            print(f"{label} 가 없다: {path}\n먼저 python -m app.db.init_db 를 실행한다.")
            return 1

    foods, rules = connect_foods(), connect_rules()
    try:
        result = recalc_expiry(foods, rules, dry_run=args.dry_run)
    finally:
        foods.close()
        rules.close()

    for name, purchase, old, new in result["changed"]:
        print(f"{name} (구매일 {purchase}): {old} -> {new}")
    for name, purchase, reason in result["skipped"]:
        print(f"건너뜀 {name} (구매일 {purchase}): {reason}")
    verb = "바뀔" if args.dry_run else "바꾼"
    print(f"{verb} 식품 {len(result['changed'])}건, 그대로 {result['same']}건, 건너뜀 {len(result['skipped'])}건")
    if args.dry_run:
        print("(--dry-run: 저장하지 않았다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
