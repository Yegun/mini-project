# app/db — 저장소(PostgreSQL) 사용 설명서

API 를 만드는 분이 가져다 쓰는 용도의 설명서다. 표 구조의 근거는 [DATA-MODEL.md](../../../DATA-MODEL.md), 창구와의 연결은 DATA-MODEL 6절.

## 준비 (.env)

`.env` 는 Git 에 올리지 않는다. 키 이름은 [.env.example](../../../.env.example) 에 있다. 연결 문자열·비밀번호는 채팅과 문서에 쓰지 않는다.

| 키 | 용도 |
|---|---|
| `DATABASE_URL` | 앱(API)이 쓰는 DB 계정. 규칙표 세 표는 **읽기만** 된다 (Q-16) |
| `DATABASE_ADMIN_URL` | 개발자 계정. 표 만들기·규칙표 채우기·기한 다시 계산에만 쓴다 |
| `APP_DB_USER`, `APP_DB_PASSWORD` | 앱 계정을 만들 때(`setup_roles`) 쓴다 |
| `TEST_DATABASE_URL` | 시험용 DB. 시험이 임시 schema 를 만들고 지운다. 운영 DB 를 넣지 않는다 |

## 표 만들기 · 규칙표 채우기 (개발자, backend 폴더에서)

```
python -m app.db.migrate       # 표 7개 만들기 (번호 순서대로 한 번씩, 여러 번 실행해도 안전)
python -m app.db.init_db       # 표 만들기 + 규칙표 30개 채우기 (여러 번 실행해도 같은 결과, 식품·계정은 그대로)
python -m app.db.setup_roles   # 앱 계정 만들기 (규칙표 읽기 전용)
```

- 표 정의는 `migrations/0001_create_tables.sql`. 나중에 표를 바꿀 때는 `0002_...sql` 처럼 번호를 올려 새 파일을 더한다 (이미 실행한 파일은 고치지 않는다).
- 규칙표 값은 [seed_rules.py](seed_rules.py) 에 있고 정식값이다. 고친 뒤 `init_db` 를 다시 돌린다.

## 연결

```python
from app.db.connection import connect_app
conn = connect_app()   # psycopg 연결. 칸 이름으로 읽는 dict 를 돌려준다. 끝나면 conn.close()
```

- **저장소 함수는 commit 하지 않는다.** 요청 하나를 한 묶음으로 처리하도록 부르는 쪽이 끝에 `conn.commit()`, 실패하면 `conn.rollback()` 한다 (API-SPEC 0절). `app/database.py` 의 `transaction()` 이 이 일을 하게 바꾸면 된다.
- 식품·계정·규칙표가 한 DB 안에 있으므로 **연결 하나로 모두 읽는다.** (예전에는 식품 연결과 규칙표 연결이 따로였다.)
- "오늘"은 DB 시계가 아니라 API 의 `get_today()` 를 인자로 넘긴다 (D-088). 날짜는 `"2026-10-30"` 글자로 주고받는다.
- 잘못된 값은 DB 가 한 번 더 막고 `psycopg.errors.CheckViolation` 등을 낸다. API 검사를 통과한 값이 걸렸다면 API 검사가 빠진 것이므로 `server_error` 로 다룬다. DB 에 닿지 못하면 `psycopg.OperationalError` 다.

## 계정 — `users_repo`

| 함수 | 하는 일 | API |
|---|---|---|
| `create_user(conn, email, password)` | 계정을 만든다 (이메일은 공백 제거·소문자). 돌려주는 값 `{"id", "email"}`. 이미 있으면 `EmailTaken` (동시 가입도 같다) | B1 |
| `authenticate(conn, email, password)` | 맞으면 `{"id", "email"}`, 아니면 `None` (이메일 없음과 비밀번호 틀림을 구분하지 않는다) | B2 |
| `find_user_by_email`, `hash_password`, `verify_password` | 낱개로 쓸 때 | — |

비밀번호는 argon2 해시 문자열 하나로 저장한다 (솔트는 그 안에 있다). 이메일 모양·비밀번호 규칙(8자·영문·숫자·특수문자) 검사는 API 가 한다.

## 로그인 상태 — `sessions_repo`

| 함수 | 하는 일 | API |
|---|---|---|
| `create_session(conn, user_id)` | 이 기기의 로그인 상태를 만들고 **쿠키 `session` 에 담을 값**을 돌려준다. 그 계정의 만료된 줄도 지운다 | B1, B2 |
| `check_session(conn, token)` | 살아 있으면 마지막 사용 시각을 갱신하고 `user_id` 를 돌려준다. 없거나 30분이 지났으면 `None` (`login_required`) | 모든 🔒 |
| `delete_session(conn, token)` | 이 기기 줄 하나만 지운다 | B3 |

- DB 에는 쿠키 값의 해시만 저장한다. 30분은 DB 시계로 센다.
- ⚠️ `check_session` 이 `None` 을 돌려줄 때도 만료된 줄을 지웠으므로 **`login_required` 를 응답하기 전에 commit** 한다.

## 식품 — `foods_repo`

모든 함수의 두 번째 인자가 계정 번호(`user_id`)다. 없는 식품·남의 식품·(홈·상세에서) 처리된 식품·UUID 모양이 아닌 번호는 모두 똑같이 `None` / `False` 다 (`not_found`).

| 함수 | 하는 일 | API |
|---|---|---|
| `create_food(conn, user_id, name=, storage=, quantity=, unit=, purchase_date=, expiry_date=, source=)` | 내 식품으로 만든다. 번호는 DB 가 만들고 `status='none'` | A2, A3 |
| `get_food(conn, user_id, id, include_processed=False)` | 한 건. 기본은 처리 전 식품만 | A4 |
| `list_active_foods(conn, user_id)` | 홈 목록. 기한 → 구매일 → 이름순(글자 코드) | A1 |
| `update_food(conn, user_id, id, name=..., ...)` | 고칠 칸만 넘긴다 (`name, storage, quantity, unit, purchase_date, expiry_date, source`) | A5, A6 |
| `set_status(conn, user_id, id, "eaten"/"discarded", processed_date)` | 처리. `processed_date` 는 API 가 정한 오늘 | A7 |
| `restore_food(conn, user_id, id)` | 홈으로 되돌리기. 처리 상태 none, 처리한 날짜 비움 | D3 |
| `delete_food(conn, user_id, id)` | 행을 지운다. 지웠으면 `True` | A8 |
| `list_processed_foods(conn, user_id)` | `{"eaten": [...], "discarded": [...]}`. 최근 처리한 순 → 이름순. 줄은 `id, name, quantity, unit, processed_date` | D2 |

식품 한 건: `{"id", "name", "storage", "quantity", "unit", "purchase_date", "expiry_date", "source", "status", "processed_date"}`. 날짜는 글자, `processed_date` 는 없으면 `None`, `user_id` 는 내보내지 않는다. 여유·주의 같은 계산 칸은 API 가 붙인다.

## 규칙표 — `rules_repo` (읽기 전용)

| 함수 | 하는 일 | API |
|---|---|---|
| `search_rules(conn, q)` | 이름·별칭에 `q` 가 **들어 있으면** 찾는다. 이름순, 빈 검색어는 `[]` | C1 |
| `find_rule(conn, name)` | 이름 **또는 별칭**이 정확히 같은 식품. 별칭이어도 정식 이름의 규칙을 돌려준다 | A2, A3, A5 |
| `get_rule_by_name(conn, name)` | 정식 이름이 정확히 같은 것 (식품에 저장된 이름으로 규칙을 찾을 때) | A5, A6 |
| `get_rule(conn, id)`, `list_rules(conn)` | 한 건 / 전체 | — |

규칙표 한 건: `{"id", "name", "default_storage", "storages": [{"storage", "allowed", "max_days"}, ...]}` (상온·냉장·냉동 순). `allowed` 가 `False` 면 "불가"이고 `max_days` 는 `None`. 규칙표의 "불가" 보관 방법을 거절하는 것은 API 가 한다.

## 기록 — `records_repo`

`records_summary(conn, user_id, today)` (D1) → `{"eaten": {"year","month"}, "discarded": {...}, "food_kinds", "by_storage": {...}, "expiry_dates": [...]}`.
식품 상태별 수(여유·주의·임박·지남)는 홈 목록과 같은 판정(`app/status.py`)을 써야 해서, DB 는 처리 전 식품의 **기한 목록(`expiry_dates`)** 만 주고 API 가 `by_status` 로 센다. 지난 지 4일 이상 식품도 포함되어 있다.

## 기존 식품 옮기기 — `legacy_migration`

| 함수 | 부르는 때 |
|---|---|
| `register_first_user(conn, user_id)` | **가입 묶음 안에서**, 계정을 만든 직후. 첫 계정이면 `True` |
| `migrate_legacy_foods(conn, user_id, today)` | 가입 묶음을 commit **한 뒤**(첫 계정일 때), 그리고 로그인할 때 `needs_migration` 이 `True` 이면. 성공 `True` |
| `needs_migration(conn, user_id)` | 로그인할 때 |

- 옮기다 실패하면 옮김 묶음만 취소되고 **예외가 나온다. 가입·로그인은 성공으로 처리하고 예외는 삼킨다** (D-097). 가입 commit 을 먼저 해 두어야 한다.
- 옛 SQLite 파일(`backend/data/fridge.db`, 환경 변수 `FRIDGE_DB_PATH`)은 읽기 전용으로만 열고 지우지 않는다 (D-098).

## 규칙표를 고친 뒤 — 기한 다시 계산 (개발자용)

```
python -m app.db.recalc_expiry --dry-run   # 저장하지 않고 바뀔 내용만 본다
python -m app.db.recalc_expiry             # 저장한다
```

대상은 모든 계정의 `source = rule`, `status = none` 식품. 새 기한 = 구매일 + 지금 보관 방법의 새 `max_days`. 직접 등록·처리된 식품은 그대로. 이름이 규칙표에 없거나 보관 방법이 "불가"가 된 식품은 건너뛰고 알려 준다. 보관 방법을 바꾼 적 있는 식품은 이 계산으로 처음 계산식으로 돌아갈 수 있다 (Q-26).

## API 담당이 합칠 때 바꿔야 할 곳

- `app/database.py`: SQLite 연결·`get_foods_conn`·`get_rules_conn` 을 `connect_app()` 하나로, `transaction()` 이 `psycopg.Error` 를 500 으로 바꾸게. `get_today()` 는 한국 시간으로.
- `app/foods_store.py`·`services.py`·`routers/`: 저장소 함수에 `user_id` 가 첫 인자로 들어가고, 처리(`set_status`)에 오늘 날짜가 들어간다. 규칙표 이름 확인은 `find_rule`(별칭 포함).
- `app/main.py`: 시작할 때 `ensure_db()` 는 개발자 계정이 필요하다. 운영에서는 `migrate`·`init_db` 를 미리 실행하고 서버 시작에서 빼도 된다.
- `tests/conftest.py` 의 SQLite 시험용 창고와 `test_api_*`, `test_ensure_db.py`, `test_real_files.py` 는 새 저장소에 맞춰 고쳐야 한다.
- 옛 `app/db/schema.py`(SQLite 표 정의)는 더 쓰이지 않는다.

## 알아 둘 것

- **DB 는 저장만 한다.** 기한 계산, 상태 판정, 오늘 날짜, 입력 검사 메시지, 규칙표의 "불가" 보관 방법 거절은 API 가 한다.
- 수량의 "소수 둘째 자리까지"와 "정수 8자리"(D-027, Q-05)는 API 가 먼저 검사해야 한다. 소수 셋째 자리는 DB 가 조용히 반올림하고, 8자리를 넘으면 오류를 낸다.
- 처리된(다 먹음·버림) 식품은 `get_food`·`update_food`·`delete_food` 에서 없는 식품과 같다. 보려면 `include_processed=True`, 되돌리려면 `restore_food`.
- 같은 식품을 두 기기에서 동시에 고치면 마지막에 저장한 것이 이긴다 (Q-20).
