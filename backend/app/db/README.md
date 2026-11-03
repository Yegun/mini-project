# app/db — 저장소(PostgreSQL) 사용 설명서

API 를 만드는 분이 가져다 쓰는 용도의 설명서다. 표 구조의 근거는 [DATA-MODEL.md](../../../DATA-MODEL.md), 창구와의 연결은 DATA-MODEL 6절.

## 준비 (.env)

`.env` 는 Git 에 올리지 않는다. 키 이름은 [.env.example](../../../.env.example) 에 있다. 연결 문자열·비밀번호는 채팅과 문서에 쓰지 않는다.

| 키 | 용도 |
|---|---|
| `DATABASE_URL` | 앱(API)이 쓰는 DB 계정. 규칙표는 **읽기와 더하기만** 된다 (Q-27). RLS 를 건너뛰는 속성(BYPASSRLS)이 있어야 한다 (Q-33) |
| `DATABASE_ADMIN_URL` | 개발자 계정. 표 만들기(알렘빅)·규칙표 채우기·기한 다시 계산에만 쓴다 |
| `APP_DB_USER`, `APP_DB_PASSWORD` | 앱 계정을 만들 때(`setup_roles`) 쓴다 |
| `TEST_DATABASE_URL` | 시험용 DB. 시험이 임시 schema 를 만들고 지운다. **내 컴퓨터(localhost) 주소가 아니면 시험이 멈춘다** |

## 표 만들기 · 버전 관리 · 규칙표 채우기 (개발자, backend 폴더에서)

표는 **알렘빅(Alembic)** 으로 버전을 관리한다. 버전 파일은 `alembic/versions/` 에 있고 번호 순서대로 한 번씩만 적용된다. DB 가 어느 버전까지 적용됐는지는 DB 안의 `alembic_version` 표에 기록된다 (내 컴퓨터 DB 와 클라우드 DB 가 따로 기록을 가진다).

```
python -m app.db.migrate        # 최신 버전까지 올린다 (= alembic upgrade head)
python -m app.db.migrate down   # 한 단계 되돌린다 (= alembic downgrade -1)
python -m app.db.init_db        # 최신 버전까지 올리고 규칙표 30개를 채운다 (여러 번 실행해도 같은 결과, 식품·계정은 그대로)
python -m app.db.setup_roles    # 앱 계정 만들기 (규칙표 읽기·더하기, RLS 건너뛰기)
alembic current                 # 지금 DB 의 버전 / alembic history  # 전체 이력
```

- 현재 버전 (한 버전 = 한 가지 일, 앞 단계가 되어 있어야 다음이 된다):

| 번호 | 하는 일 | 종류 |
|---|---|---|
| 0001 | 새 DB 구조 만들기 (`foods.user_id` 는 **비울 수 있게**) | 구조 |
| 0002 | 옛 식품(SQLite `backend/data/fridge.db`)을 `foods` 로 가져오기, **주인 없이**. 파일이 있는 컴퓨터에서 올릴 때만 가져온다 | 데이터 |
| 0003 | 이전용 계정(`legacy@fridge.invalid`, 로그인 불가) 만들기 | 데이터 |
| 0004 | 주인 없는 식품을 모두 이전용 계정에 넘기기 | 데이터 |
| 0005 | `foods.user_id` 를 비울 수 없게 + 외래키 (주인 없는 식품이 남아 있으면 이 단계가 실패) | 구조 |
| 0006 | 수파베이스 REST API 역할(anon·authenticated)의 표 권한 회수 (그 역할이 없는 DB 에서는 아무것도 안 한다) | 보안 |
| 0007 | 옮김 기록 표 `legacy_migration` 만들기(첫 계정과 옮김 여부, 줄 1개). 이미 실제 가입자가 있고 이전용 계정에 식품이 없는 DB 는 "옮김 끝"으로 적는다 | 구조 |
| 0008 | 사진 읽기 결과 표 `photo_analyses` 만들기(계정마다 한 줄, 30분) + **표 8개에 RLS 켜기**(정책 없음). 앱 계정에 BYPASSRLS 가 없으면 이 단계 뒤 앱이 줄을 하나도 못 본다 | 구조·보안 |

- 첫 가입자가 이전용 계정의 식품을 넘겨받는 마지막 단계는 서버가 한다 (아래 "기존 식품 넘겨받기").
- 표를 바꿀 때는 `alembic revision -m "설명"` 으로 새 파일을 만들고 `upgrade()` 와 `downgrade()` 에 **SQL 을 직접 쓴다** (`op.execute`). 이미 적용한 파일은 고치지 않는다. 파일 하나가 한 묶음이라 중간에 실패하면 그 파일은 아무것도 바뀌지 않는다.
- 접속은 `.env` 의 `DATABASE_ADMIN_URL` 을 쓴다. **표는 알렘빅으로만 바꾼다.** 수파베이스 화면에서 표를 직접 고치면 버전 기록과 어긋난다.
- 수파베이스에서는 표를 바꿀 때 Transaction pooler(6543)가 아니라 **Direct connection 또는 Session pooler(5432)** 주소를 쓴다.
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
| `verify_user_password(conn, user_id, password)` | 로그인한 계정의 비밀번호가 맞는지. 비었거나 글자가 아닌 값은 틀린 것과 같다 | H1 |
| `delete_user(conn, user_id)` | 계정 한 줄을 지운다. 식품(처리한 식품 포함)·로그인 상태(모든 기기)·사진 읽기 결과는 DB 가 따라 지운다. 옮김 기록은 줄이 남고 `user_id` 만 비워진다. 규칙표는 그대로 | H1 |
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

## 규칙표 — `rules_repo` (읽기와 더하기)

| 함수 | 하는 일 | API |
|---|---|---|
| `search_rules(conn, q)` | 이름·별칭에 `q` 가 **들어 있으면** 찾는다. 이름순, 빈 검색어는 `[]` | C1 |
| `find_rule(conn, name)` | 이름 **또는 별칭**이 정확히 같은 식품. 별칭이어도 정식 이름의 규칙을 돌려준다 | A2, A3, A5 |
| `get_rule_by_name(conn, name)` | 정식 이름이 정확히 같은 것 (식품에 저장된 이름으로 규칙을 찾을 때) | A5, A6 |
| `get_rule(conn, id)`, `list_rules(conn)` | 한 건 / 전체 | — |
| `add_rule(conn, name, default_storage, storages)` | 규칙표에 새 식품을 **더한다**(별칭 없음). 번호는 이름에서 계산. 이미 있는 이름이거나 다른 식품의 별칭이면 아무것도 안 하고 `False` | F2 |

규칙표 한 건: `{"id", "name", "default_storage", "storages": [{"storage", "allowed", "max_days"}, ...]}` (상온·냉장·냉동 순). `allowed` 가 `False` 면 "불가"이고 `max_days` 는 `None`. 규칙표의 "불가" 보관 방법을 거절하는 것은 API 가 한다.

앱 계정은 규칙표에 **읽기와 더하기만** 한다(`add_rule` 뿐). 이미 있는 줄을 고치거나 지우는 것과 별칭을 더하는 것은 개발자 계정만 한다 (Q-27). 같은 이름을 두 요청이 동시에 더해도 한 줄만 만들어지고 먼저 저장된 값이 남는다 (Q-30).

## 사진 읽기 결과 — `photo_analyses_repo`

사진 한 장을 읽은 결과(글만)를 계정마다 한 줄, 30분 동안 잠깐 보관한다. 사진은 저장하지 않는다 (D-102).

| 함수 | 하는 일 | API |
|---|---|---|
| `save_analysis(conn, user_id, items)` | 이 계정의 이전 결과를 지우고 새로 보관한다. 새 번호(`analysis_id`)를 돌려준다 | F1 |
| `get_valid_analysis(conn, user_id, analysis_id)` | 내 결과이고 30분 안이면 `{"id", "items", "created_at"}`, 아니면 `None` (`analysis_expired`). **만료된 줄이면 그 줄을 지우고 `None`** — 그래서 `None` 이어도 commit 해야 지운 것이 남는다 | F2 |
| `delete_analysis(conn, user_id, analysis_id)` | 쓴 결과를 지운다. 지웠으면 `True` | F2 |
| `delete_expired(conn, user_id)` | 그 계정의 만료된 결과를 지운다. 로그인할 때 `create_session` 이 부른다 | B1, B2 |

- 남의 번호·없는 번호·UUID 모양이 아닌 번호는 모두 똑같이 `None` 이다 (D-063).
- 시각은 DB 시계다 (Q-13). 새 사진을 올리면 이전 번호는 쓸 수 없게 된다 (Q-29). 계정을 지우면 따라 지워진다 (Q-09).

## 기록 — `records_repo`

`records_summary(conn, user_id, today)` (D1) → `{"eaten": {"year","month"}, "discarded": {...}, "food_kinds", "by_storage": {...}, "expiry_dates": [...]}`.
식품 상태별 수(여유·주의·임박·지남)는 홈 목록과 같은 판정(`app/status.py`)을 써야 해서, DB 는 처리 전 식품의 **기한 목록(`expiry_dates`)** 만 주고 API 가 `by_status` 로 센다. 지난 지 4일 이상 식품도 포함되어 있다.

## 기존 식품 넘겨받기 — `legacy_migration`

옛 SQLite 식품을 가져오는 일은 서버가 아니라 알렘빅 버전 파일(0002 ~ 0004)이 한다. 가져온 식품은 로그인할 수 없는 **이전용 계정**이 맡고 있다.

| 함수 | 부르는 때 |
|---|---|
| `register_first_account(conn, user_id)` | **가입 묶음 안에서**, 계정을 만든 직후. 첫 계정이면 `legacy_migration` 에 적고 `True` |
| `claim_if_first_account(conn, user_id)` | **가입·로그인 직후 별도 묶음에서**. 첫 계정이고 아직 못 넘겨받았으면 식품을 넘기고 `migrated` 를 참으로 한다. 넘긴 수를 돌려준다(아니면 0) |
| `claim_legacy_foods(conn, user_id)` | 위 함수가 쓰는 낱개. 이전용 계정이 맡은 식품을 이 계정으로 넘기고 넘긴 수를 돌려준다 |

- 첫 계정만 받는다. 이후 가입하는 계정은 넘겨받을 것이 없어서 빈 상태다 (D-044). 두 사람이 동시에 처음 가입해도 `legacy_migration` 의 줄은 한 개(id = 1)라 한 사람만 첫 계정이 되고, 넘길 때도 그 줄을 잠근다.
- 넘기기는 가입과 **다른 묶음**이다. 실패하면 넘기기만 취소되고(식품과 `migrated` 표시가 함께 원래대로) 가입·로그인은 성공한다. 첫 계정이 다음에 로그인할 때 성공할 때까지 다시 시도한다 (D-097). 실패는 서버 기록(log)에 남는다.
- 이전용 계정 이메일은 `LEGACY_EMAIL` (알렘빅 0003·0004 와 같은 값, 시험이 확인한다).
- 옛 SQLite 파일은 읽기 전용으로만 열고 지우지 않는다 (D-098). 위치는 환경 변수 `FRIDGE_DB_PATH` (기본 `backend/data/fridge.db`).

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

## AI 연동 (`app/ai.py`, 저장소 아님)

API 가 AI(Claude)를 부르는 곳은 `app/ai.py` 한 곳뿐이다 (D-132). 키는 `.env` 의 `ANTHROPIC_API_KEY` 에서만 읽고, 모델은 `AI_MODEL`(없으면 `claude-haiku-5-5`)로 바꾼다. 음식 추천은 30초까지 기다리고 자동으로 다시 부르지 않는다. 시험은 가짜 클라이언트를 쓰므로 키가 없어도 돈다.

## 알아 둘 것

- 표 8개에 RLS 가 켜져 있고 정책은 없다 (0008, Q-33). 앱 계정은 `setup_roles` 가 주는 BYPASSRLS 로 건너뛰고, "내 식품만"은 API 가 `user_id` 조건으로 지킨다. 수파베이스에서 BYPASSRLS 를 줄 수 있는지는 클라우드 DB 에 적용할 때 확인한다.
- **DB 는 저장만 한다.** 기한 계산, 상태 판정, 오늘 날짜, 입력 검사 메시지, 규칙표의 "불가" 보관 방법 거절은 API 가 한다.
- 수량의 "소수 둘째 자리까지"와 "정수 8자리"(D-027, Q-05)는 API 가 먼저 검사해야 한다. 소수 셋째 자리는 DB 가 조용히 반올림하고, 8자리를 넘으면 오류를 낸다.
- 처리된(다 먹음·버림) 식품은 `get_food`·`update_food`·`delete_food` 에서 없는 식품과 같다. 보려면 `include_processed=True`, 되돌리려면 `restore_food`.
- 같은 식품을 두 기기에서 동시에 고치면 마지막에 저장한 것이 이긴다 (Q-20).
