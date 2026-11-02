"""규칙표 값을 고친 뒤 한 번 돌리는 개발자 작업. 등록된 규칙표 식품의 기한을 다시 계산해 저장한다.

ARCHITECTURE 4-3, DATA-MODEL 5-3 을 따른다.
- 대상: source = rule, status = none 인 식품 (모든 계정). 직접 등록(manual)과 처리된 식품은 건드리지 않는다.
- 새 기한 = 구매일 + 지금 보관 방법의 새 max_days (A2 계산식). 상태 색은 저장하지 않으므로 따로 할 일이 없다.
- 규칙표는 읽기만 한다 (D-007). 앱·API 에서는 부르지 않는다. 개발자 계정(DATABASE_ADMIN_URL)으로만 돌린다.
- 한 번에 성공하거나, 실패하면 아무것도 바뀌지 않는다 (API-SPEC 0절).
- 보관 방법을 바꾼 적 있는 식품은 이 계산으로 기한이 구매일 + max_days 로 되돌아갈 수 있다 (이력을 저장하지 않는다, D-024. Q-26).

문서에 처리 방법이 없는 식품은 계산하지 않고 건너뛴 뒤 알려 준다.
- 이름이 규칙표에 없다
- 지금 보관 방법이 규칙표에서 "불가"가 됐다

사용: backend 폴더에서  python -m app.db.recalc_expiry [--dry-run]
  --dry-run  저장하지 않고 바뀔 내용만 보여 준다
"""
import argparse
import sys

import psycopg

from app.calc import expiry_from_days
from app.db.connection import connect_admin
from app.db.rules_repo import get_rule_by_name

_TARGETS = (
    "SELECT id, name, storage, purchase_date, expiry_date FROM foods"
    " WHERE source = 'rule' AND status = 'none' ORDER BY purchase_date, name COLLATE \"C\", id"
)
_UPDATE = "UPDATE foods SET expiry_date = %s WHERE id = %s AND source = 'rule' AND status = 'none'"


def recalc_expiry(conn: psycopg.Connection, *, dry_run: bool = False) -> dict:
    """결과: {"changed": [(이름, 구매일, 옛 기한, 새 기한)], "same": 개수, "skipped": [(이름, 구매일, 이유)]}

    commit 은 하지 않는다 (main 이 한다).
    """
    changed, skipped, updates, same = [], [], [], 0
    for row in conn.execute(_TARGETS).fetchall():
        rule = get_rule_by_name(conn, row["name"])
        if rule is None:
            skipped.append((row["name"], row["purchase_date"].isoformat(), "규칙표에 없는 이름"))
            continue
        info = next((s for s in rule["storages"] if s["storage"] == row["storage"]), None)
        if info is None or not info["allowed"]:
            skipped.append((row["name"], row["purchase_date"].isoformat(), "지금 보관 방법이 규칙표에서 불가"))
            continue
        new_expiry = expiry_from_days(row["purchase_date"], info["max_days"])
        if new_expiry == row["expiry_date"]:
            same += 1
            continue
        changed.append(
            (row["name"], row["purchase_date"].isoformat(), row["expiry_date"].isoformat(), new_expiry.isoformat())
        )
        updates.append((new_expiry, row["id"]))
    if updates and not dry_run:
        with conn.transaction():  # 하나라도 실패하면 모두 되돌린다
            for params in updates:
                conn.execute(_UPDATE, params)
    return {"changed": changed, "same": same, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="규칙표 식품의 기한을 규칙표 값으로 다시 계산한다.")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 바뀔 내용만 보여 준다")
    args = parser.parse_args(argv)

    conn = connect_admin()
    try:
        result = recalc_expiry(conn, dry_run=args.dry_run)
        conn.commit()
    finally:
        conn.close()

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
