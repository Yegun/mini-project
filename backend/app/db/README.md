# app/db — 저장소(SQLite) 사용 설명서

API 를 만드는 분이 가져다 쓰는 용도의 설명서다. 표 구조의 근거는 [DATA-MODEL.md](../../../DATA-MODEL.md).

## DB 만들기

backend 폴더에서 한 번 실행한다. 여러 번 실행해도 같은 결과이고, 식품 데이터는 지워지지 않는다.

```
python -m app.db.init_db
```

- `backend/data/fridge.db` (식품), `backend/data/rules.db` (규칙표) 가 만들어진다. Git 에는 올라가지 않는다 (`*.db` 무시).
- 위치를 바꾸려면 환경 변수 `FRIDGE_DB_PATH`, `RULES_DB_PATH` 를 쓴다.
- ⚠️ 규칙표의 이름 30개는 확정이지만, **기본 보관 방법·가능 여부·최대 보관 일수·별칭은 임시값**이다 ([seed_rules.py](seed_rules.py) 맨 위 참고). 식약처 기준으로 확정되면 그 파일만 고치고 위 명령을 다시 실행한다.

## 연결

```python
from app.db.connection import connect_foods, connect_rules
foods = connect_foods()   # 읽기·쓰기
rules = connect_rules()   # 읽기 전용 (쓰면 오류)
```

## 식품 — `foods_repo`

날짜는 `"2026-10-30"` 글자, 값은 D-032 영어 이름(`room/fridge/freezer`, `rule/manual`, `none/eaten/discarded`). 결과는 dict.

| 함수 | 하는 일 | API |
|---|---|---|
| `create_food(conn, name=, storage=, quantity=, unit=, purchase_date=, expiry_date=, source=)` | 만든다. 번호(UUID)와 `status='none'` 은 자동 | A3, A4 |
| `get_food(conn, id)` | 한 건. 없거나 처리된 식품이면 `None` | A5 |
| `list_active_foods(conn)` | 처리 전 식품. 기한 → 구매일 → 이름순 | A1 |
| `update_food(conn, id, name=..., ...)` | 고칠 칸만 넘긴다 (`name, storage, quantity, unit, purchase_date, expiry_date, source`). 없거나 처리된 식품이면 `None` | A6, A7 |
| `set_status(conn, id, "eaten"/"discarded")` | 처리. 행은 남는다. 없거나 이미 처리됐으면 `None` | A8 |
| `delete_food(conn, id)` | 행을 지운다. 지웠으면 `True`, 없거나 처리된 식품이면 `False` | A9 |

## 규칙표 — `rules_repo` (읽기 전용)

| 함수 | 하는 일 | API |
|---|---|---|
| `search_rules(conn, q)` | 이름·별칭에 `q` 가 **들어 있으면** 찾는다. 빈 검색어는 `[]` | A2 |
| `get_rule_by_name(conn, name)` | 이름이 정확히 같은 것 ("규칙표에 있는 이름인가") | A6 |
| `get_rule(conn, rule_id)`, `list_rules(conn)` | 한 건 / 전체 | — |

규칙표 한 건: `{"id", "name", "default_storage", "storages": [{"storage", "allowed", "max_days"}, ...]}` (상온·냉장·냉동 순). `allowed` 가 `False` 면 "불가"이고 `max_days` 는 `None`.

## 알아 둘 것

- **DB 는 저장만 한다.** 기한 계산, 상태 판정, 오늘 날짜, 입력 검사 메시지, 규칙표의 "불가" 보관 방법 거절은 API 가 한다.
- 잘못된 값(수량 0 이하, 구매일 > 기한, 이상한 날짜·보관 방법 등)은 DB 가 한 번 더 막고 `sqlite3.IntegrityError` 를 낸다. 쉬운 오류 메시지로 바꾸는 것은 API 몫이다.
- 쓰기 함수는 실패하면 아무것도 바뀌지 않는다.
- 수량의 "소수 둘째 자리까지"(D-027)는 DB 가 확인하지 않는다. API 가 검사한다.
- 처리된(다 먹음·버림) 식품은 조회·수정·삭제가 모두 막혀 있다 (`None`/`False`).
- 규칙표 검색의 "들어 있으면 찾기" 방식은 아직 DECISIONS 에 적히지 않았다.
