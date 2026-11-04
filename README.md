# 냉장고 관리 웹 앱

장 본 식품을 등록하면 보관 방법과 먹어야 할 기한을 **막대 달력과 색**으로 한눈에 보여 주고, 기한을 놓쳐 버리는 일을 줄여 주는 웹 앱입니다. 영수증 · 장바구니 **사진 한 장**으로 식품을 한꺼번에 등록하고(AI), 가진 식품으로 **음식을 추천**받을 수 있습니다.

- 운영 주소: https://mini-project-iota-virid.vercel.app
- 버전: v1.0.0 (Vercel 배포)
- 조: 유통기한-2조 (박경빈, 안형철, 양수빈)

## 목차

1. [쓰는 기술과 폴더](#1-쓰는-기술과-폴더)
2. [처음 한 번: 준비하기](#2-처음-한-번-준비하기)
3. [Supabase(DB) 연결 안내](#3-supabasedb-연결-안내)
4. [백엔드 실행법](#4-백엔드-실행법)
5. [프론트엔드 실행법](#5-프론트엔드-실행법)
6. [시험과 검사](#6-시험과-검사)
7. [Vercel 배포하기](#7-vercel-배포하기)
8. [막혔을 때](#8-막혔을-때)
9. [문서 안내](#9-문서-안내)
10. [제품 기준점 (v1.0.0)](#10-제품-기준점-v100)
11. [작업 규칙](#11-작업-규칙)

---

## 1. 쓰는 기술과 폴더

| 부분 | 기술 |
|---|---|
| 화면 | React 19 · TypeScript · Vite |
| API | Python 3.12 이상 · FastAPI |
| 저장소 | PostgreSQL (클라우드, Supabase) |
| AI | Claude (Haiku 5.5, 설정으로 바꿀 수 있음) |
| 배포 | Vercel (화면과 API 를 함수 하나로) |

```
mini-project/
├─ api/              Vercel 함수 파일 (index.py): API 를 /api 에, 화면을 / 에 붙임
├─ backend/          FastAPI 앱
│  ├─ app/           API 코드 (routers/ 창구, db/ 저장소)
│  ├─ alembic/       DB 표 버전 관리
│  └─ tests/         시험
├─ frontend/         React 화면 (src/, 빌드하면 dist/)
├─ docs/             버전별 문서와 검수 기록
├─ vercel.json       Vercel 빌드 설정
├─ .vercelignore     Vercel 에 올리지 않을 것
├─ requirements.txt  Vercel 이 설치할 파이썬 패키지 (uv export 로 만든 파일)
└─ .env.example      환경 변수 이름 예시 (값은 없음)
```

- 화면은 저장소를 직접 만지지 않습니다. **저장소와 AI 는 API 만 만집니다.**
- 비밀 값(DB 주소 · AI 키)은 `.env` 와 Vercel 환경 변수에만 둡니다. Git · 채팅 · 문서에 적지 않습니다.

---

## 2. 처음 한 번: 준비하기

필요한 것

| 도구 | 확인 | 용도 |
|---|---|---|
| Node.js 22 | `node -v` | 화면 |
| Python 3.12 이상, [uv](https://docs.astral.sh/uv/) | `uv --version` | API |
| Git | `git --version` | 저장소 |
| (배포할 때) Vercel CLI | `vercel --version` | 7절 |

**1) 저장소 받기**

```
git clone https://github.com/Yegun/mini-project.git
cd mini-project
```

**2) `.env` 만들기** — 값은 사람이 직접 적습니다.

```
copy .env.example backend\.env
```

`backend\.env` 를 열어 [`.env.example`](.env.example) 의 이름 옆에 값을 채웁니다. 이 파일은 `.gitignore` 에 있어 Git 에 올라가지 않습니다.

| 이름 | 뜻 | 어디서 쓰나 |
|---|---|---|
| `DATABASE_URL` | **앱이 쓰는** DB 계정 주소 | 서버(로컬 · 배포 모두) |
| `ANTHROPIC_API_KEY` | AI(Claude) 키 | 사진 읽기 · 음식 추천 · AI 조언 |
| `AI_MODEL` | 쓸 모델 이름 (없으면 `claude-haiku-5-5`) | 선택 |
| `DATABASE_ADMIN_URL` | 개발자 DB 계정 주소 | 표 만들기 · 규칙표 채우기에만 (**배포 환경에는 넣지 않음**) |
| `APP_DB_USER`, `APP_DB_PASSWORD` | 앱 DB 계정을 만들 때 쓰는 이름과 비밀번호 | `setup_roles` 할 때만 |
| `TEST_DATABASE_URL` | 시험용 DB (내 컴퓨터의 PostgreSQL) | 시험 |

**3) 패키지 설치**

```
cd backend
uv sync
cd ..\frontend
npm install
```

---

## 3. Supabase(DB) 연결 안내

데이터(계정 · 식품 · 규칙표)는 **클라우드 PostgreSQL(Supabase)** 에 있습니다. 이미 만들어 둔 DB 를 같이 쓰므로, 새로 만들 때만 아래를 따라 합니다.

**연결 문자열 모양**

```
postgresql://사용자이름:비밀번호@주소:포트/DB이름
```

- 비밀번호에 `@` `:` `/` 같은 기호가 있으면 `%40` `%3A` `%2F` 처럼 바꿔 적습니다.
- 계정은 둘입니다. **개발자 계정**(`DATABASE_ADMIN_URL`, 표 만들기용)과 **앱 계정**(`DATABASE_URL`, 서버가 쓰는 계정)을 따로 둡니다.
- 배포(Vercel)처럼 요청마다 서버가 켜지는 곳은 Supabase 의 **연결 풀 주소(포트 6543)** 를 쓰는 편이 맞습니다. 풀 주소에서는 사용자 이름 뒤에 프로젝트 ID 가 붙는 형태(예: `postgres.프로젝트ID`)입니다. 이 부분이 빠지면 `no tenant identifier` 오류가 납니다 (Day 17 에 겪음).

**표 만들기 · 규칙표 채우기 · 앱 계정 만들기** (개발자, `backend` 폴더에서, 처음 한 번)

```
uv run python -m app.db.migrate      # 표를 최신 버전까지 만든다
uv run python -m app.db.init_db      # 규칙표 30개를 채운다 (여러 번 해도 같은 결과)
uv run python -m app.db.setup_roles  # 앱 DB 계정을 만든다 (규칙표는 읽기·더하기만)
```

- **새 버전이 나올 때마다** `python -m app.db.migrate` 로 표를 올립니다. 배포 환경은 이미 만들어 둔 DB 를 읽고 쓰기만 하므로 **표 만들기는 항상 내 컴퓨터에서** 합니다.
- 표 구조와 버전 이력은 [backend/app/db/README.md](backend/app/db/README.md) 에 있습니다.
- 이 DB 의 표에는 **보안 설정(RLS)** 이 켜져 있습니다. 앱 계정이 없으면 가입 · 로그인이 실패합니다.

---

## 4. 백엔드 실행법

`backend` 폴더에서 실행합니다.

```
cd backend
uv run uvicorn app.main:app --port 8000
```

- 켜지면 http://127.0.0.1:8000/health 가 `{"status":"ok"}` 를 돌려줍니다.
- 이 주소에는 `/api` 가 없습니다. 화면이 부르는 `/api/…` 는 화면의 개발 서버(5절)가 `/api` 를 떼고 넘겨 줍니다.
- 서버를 고치면 다시 켜야 합니다. 환경 변수(`.env`)는 켤 때 한 번 읽습니다. **키를 바꿨다면 서버를 껐다 켜세요.**

**배포와 똑같이 합쳐서 켜 보기** (화면 + API 를 한 서버에서)

```
cd frontend
npm run build
cd ..
uv run --project backend uvicorn api.index:app --port 8001
```

http://127.0.0.1:8001 에서 화면이, `/api/health` 에서 API 가 응답하면 Vercel 에서도 같은 구조로 동작합니다.

---

## 5. 프론트엔드 실행법

`frontend` 폴더에서 실행합니다. 백엔드(4절)를 먼저 켜 둡니다.

```
cd frontend
npm run dev
```

- http://localhost:5173 에서 열립니다. 화면의 `/api/…` 요청은 `127.0.0.1:8000` 으로 넘어갑니다 ([vite.config.ts](frontend/vite.config.ts)).
- 처음에는 로그인 화면이 보입니다. 가입하고 로그인하면 홈이 열립니다.

**백엔드 없이 화면만 보고 싶을 때 (가짜 데이터)**

```
$env:VITE_USE_MOCK='1'; npm run dev
```

로그인 없이 가짜 식품이 보입니다. 값을 바꾸면 상황을 바꿔 볼 수 있습니다.

| `VITE_USE_MOCK` | 보이는 것 |
|---|---|
| `1` | 정상 |
| `slow` | 응답이 느림 (확인 중 화면을 보기 좋음) |
| `ai-error` | AI 가 응답하지 못한 경우 |
| `empty` | 사진에서 식품을 못 찾은 경우 |
| `save-error` | 저장 실패 |

---

## 6. 시험과 검사

**화면**

```
cd frontend
npm run lint      # 코드 검사
npm run build     # 타입 검사 + 빌드 (오류가 있으면 dist 가 안 생긴다)
```

**백엔드**

```
cd backend
uv run pytest
```

- 시험은 `TEST_DATABASE_URL` 의 **내 컴퓨터(localhost) PostgreSQL** 에서만 돕니다. 주소가 localhost 가 아니면 시험이 멈춥니다. 시험이 임시 schema 를 만들고 지웁니다.
- 운영 DB 를 `TEST_DATABASE_URL` 에 넣지 마세요.

---

## 7. Vercel 배포하기

화면과 API 를 **함수 하나**로 묶어 올립니다. 구조는 [ARCHITECTURE.md](ARCHITECTURE.md) 1-1 에 있습니다.

| 파일 | 하는 일 |
|---|---|
| [api/index.py](api/index.py) | API 앱을 `/api` 에, 빌드한 화면을 `/` 에 붙입니다. **`/api` 를 먼저, 화면을 나중에** 붙입니다 |
| [vercel.json](vercel.json) | 화면 빌드 명령, 함수 지역(서울 `icn1`). **`rewrites` 는 쓰지 않습니다** (넣으면 모든 주소가 404) |
| [.vercelignore](.vercelignore) | `.env` · DB 파일 · 문서 · 시험 등을 올리지 않습니다 |
| [requirements.txt](requirements.txt) | 설치할 패키지. 손으로 고치지 않고 아래 명령으로 다시 만듭니다 |

패키지를 더했다면 목록을 다시 만듭니다.

```
cd backend
uv export --no-hashes --no-dev --no-emit-project -o ../requirements.txt
```

### 처음 배포할 때 (순서가 중요합니다)

**0) 준비**
- Vercel 계정이 있어야 합니다. 가입 이메일은 **마지막 커밋 작성자 이메일과 같아야** 합니다 (다르면 배포가 막힙니다. 8절).
- **Windows 는 개발자 모드를 켭니다** (설정 → 개발자용). 안 켜면 `EPERM: operation not permitted, symlink` 오류가 납니다.

**1) 설치와 로그인**
```
npm i -g vercel
vercel login          # 브라우저에서 승인
vercel whoami         # 내 계정 이름이 나오는지 확인
```

**2) 첫 배포 — 환경 변수 없이**
```
vercel deploy --yes
```
- 프로젝트가 만들어지고 이 폴더와 연결됩니다. 마지막 줄의 `Aliased https://….vercel.app` 가 운영 주소입니다.
- `Failed to connect … to project` 는 GitHub 연결 경고입니다. 배포에는 영향이 없습니다.

**3) 환경 변수 넣기** — 값은 묻는 자리에 **붙여 넣습니다** (명령줄에 쓰지 않습니다).
```
vercel env add DATABASE_URL production
vercel env add ANTHROPIC_API_KEY production
vercel env ls         # 두 이름이 Hidden 으로 보이는지 확인
```
- `DATABASE_URL` 은 `backend\.env` 의 **앱 계정** 주소입니다. 관리자 주소(`DATABASE_ADMIN_URL`)는 넣지 않습니다.
- 환경 변수는 넣은 **다음 배포부터** 들어갑니다.

**4) 운영 배포**
```
vercel deploy --prod --yes
```

**5) 확인** (`<주소>` 에 운영 주소를 넣습니다)
```
curl.exe -s <주소>/api/health                         # {"status":"ok"} 200
curl.exe -s -w " [%{http_code}]" <주소>/api/foods     # login_required [401]  ← 500 이면 환경 변수가 안 들어간 것
```
- 브라우저에서 주소를 열어 **로그인 → 홈에 식품이 보이는지 → 새로고침해도 로그인이 유지되는지 → 사진 읽기** 를 확인합니다. 배포가 `READY` 여도 앱이 동작하는지는 이렇게 직접 열어 봐야 압니다.

### 다시 배포할 때

코드를 고쳤으면 배포만 다시 합니다. 환경 변수는 이미 프로젝트에 저장돼 있어 다시 넣지 않습니다.

```
vercel deploy --prod --yes
```

- `--prod` 를 빼면 Preview 배포만 생기고 운영 주소는 그대로입니다. 또 Preview 에는 환경 변수가 없어 API 가 실패합니다.
- DB 표가 바뀌는 버전이면 **배포 전에 내 컴퓨터에서** `python -m app.db.migrate` 를 먼저 합니다.

### 배포 중단하기

Vercel 은 켜 둔 서버가 따로 없어 끄기 버튼이 없습니다. 막으려면 Vercel 대시보드에서 프로젝트의 접속 보호(Deployment Protection)를 켜거나 배포를 지웁니다. DB 의 데이터는 Vercel 을 지워도 그대로입니다.

---

## 8. 막혔을 때

| 증상 | 원인과 해결 |
|---|---|
| `EPERM: operation not permitted, symlink` (vercel 명령) | Windows 가 링크 만들기를 막음. **개발자 모드**를 켜고 터미널을 새로 엽니다 |
| `Your codebase isn't linked to a project on Vercel` | 아직 연결 전. `vercel deploy --yes` 를 먼저 합니다 |
| `Failed to connect … to project` | GitHub 연결 경고. 배포가 이어지면 무시해도 됩니다 |
| `/api/foods` 가 500 | `DATABASE_URL` 이 배포에 안 들어감. `vercel env ls` 로 확인하고 다시 `--prod` 배포 |
| 모든 주소가 404 | `vercel.json` 에 `rewrites` 를 넣었는지 확인 (넣지 않습니다) |
| 화면만 404 | `frontend/dist` 가 없음. `vercel.json` 이름(점이 없어야 함)과 빌드 명령을 확인 |
| `Building…` 에서 안 끝나고 `Blocked` | 마지막 커밋 작성자 이메일이 Vercel 가입 이메일과 다름. 그 이메일로 빈 커밋 하나를 만들고 다시 배포 (`git commit --allow-empty -m "chore: vercel deploy"`). GitHub 웹에서 PR 을 병합하면 작성자가 `noreply` 주소가 되어 막힐 수 있습니다 |
| 페이지를 넘길 때마다 느림 | 함수와 DB 가 멀리 있음. `vercel.json` 의 `regions` 를 DB 와 같은 지역으로 맞추고 다시 배포 |
| `no tenant identifier` (DB 연결) | Supabase 연결 풀 주소에서 사용자 이름에 프로젝트 ID 가 빠짐. 3절 |
| AI 가 응답하지 못한다는 메시지 | `ANTHROPIC_API_KEY` 가 없거나 틀림. 키를 고쳤다면 **서버를 껐다 켜야** 새 키를 읽습니다 |
| 가입 때 "비밀번호는 8자 이상이고…" | 서버가 허용하는 특수문자는 `! @ # $ % ^ & * ( ) - _ = + [ ] { } ; : , . < > / ?` 입니다. `~` 같은 기호는 거절됩니다 |

---

## 9. 문서 안내

문서는 위에서 아래로 읽습니다. 아래 단계는 위 단계를 따릅니다.

| 문서 | 내용 |
|---|---|
| [AGENTS.md](AGENTS.md) | 사람과 코딩 에이전트가 따르는 작업 규칙 |
| [TEAM.md](TEAM.md) | 조 구성, 역할 교대표, 조 규칙 |
| [PLAN.md](PLAN.md) | 날짜별 계획과 결과 (Day 16 ~) |
| [PRD.md](PRD.md) | 무엇을 · 왜 만드나. 요구사항(R-), 사용자 스토리(US-), 열린 질문(OQ-) |
| [DECISIONS.md](DECISIONS.md) | 확정한 결정과 이유 (D-번호) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 어떤 구조로 만드나. 실행 위치(1-1)와 실패 흐름(8절) 포함 |
| [USER-WORKFLOW.md](USER-WORKFLOW.md) | 사용자 업무 흐름 |
| [SCREEN-SPEC.md](SCREEN-SPEC.md) · [API-SPEC.md](API-SPEC.md) · [DATA-MODEL.md](DATA-MODEL.md) | 화면 · API · 데이터 상세 |
| [docs/version/](docs/version/) | 이전 버전(0.2.0 ~ 0.5.0)의 문서와 검수 기록, v1.0.0 검수 기록 |

---

## 10. 제품 기준점 (v1.0.0)

| 항목 | 내용 |
|---|---|
| 기준점 | 릴리즈 태그 `v1.0.0` (main 에 병합한 시점) |
| 실행 | 운영: https://mini-project-iota-virid.vercel.app. 내 컴퓨터: 4절 + 5절 |
| DB 위치 | 클라우드 PostgreSQL(Supabase). 내 컴퓨터에 DB 파일을 만들지 않습니다. 옛 SQLite 파일(`backend/data/*.db`)은 백업일 뿐 앱이 읽지 않습니다 |
| 시험 데이터 | 시험은 내 컴퓨터 PostgreSQL 의 임시 schema (`TEST_DATABASE_URL`) |
| 통과한 시나리오 | v0.5.0: SC-133 ~ SC-152, BR-104 ~ BR-118 / v1.0.0: SC-153 ~ SC-157, BR-119 ~ BR-121 (모두 통과, 직접 테스트). 이전 버전의 기록은 `docs/version/` |
| 알려진 제한 | 인터넷이 없으면 쓸 수 없음. 가입은 이메일 인증 · 로그인 횟수 제한 · 비밀번호 찾기 · 소셜 로그인이 없음. 비밀번호 특수문자는 서버가 정한 기호만 허용(화면은 더 넓게 받아서 `~` 는 서버가 거절). 직접 등록 화면의 이름 칸이 마지막으로 검색한 글자가 아니라 검색칸의 현재 글자로 채워짐. AI 요청이 배포 환경의 응답 시간 제한 안에 끝나는지의 측정값은 아직 문서에 없음(ARCHITECTURE 9절 39번) |
| 보류 기능 | 가족 냉장고 공유(R-016, R-017), 식품 보관 기간 70종 추가(#49), 임박 식품 냉동 전환 제안(#50), 임박·지남 알림 배너, 홈 화면에 앱처럼 추가(PWA), 결제 · 휴대폰 알림 |
| 재시작 방법 | 4절 → 5절 순서로 서버를 다시 켭니다. 키(`.env`)를 바꿨다면 서버를 껐다 켭니다. 운영은 `vercel deploy --prod --yes` |

---

## 11. 작업 규칙

자세한 것은 [AGENTS.md](AGENTS.md) 와 [TEAM.md](TEAM.md) 에 있습니다. 핵심만 적습니다.

- **main 에 직접 커밋하지 않습니다.** 브랜치를 만들어 작업하고, main 병합과 push 는 사람이 합니다.
- 작업 전에 PRD · ARCHITECTURE · DECISIONS 를 읽고, 계획을 보여 주고 승인받은 뒤에 작업합니다.
- 삭제 · 패키지 설치 · 대량 수정은 그때마다 다시 승인받습니다.
- **비밀 값(DB 주소 · AI 키 · 비밀번호)은 Git · 채팅 · 문서에 적지 않습니다.**
- AI 에게는 **확정(`상태: 확정`)된 문서**만 줍니다.
- 30분 막히면 강사에게 묻습니다. 무엇을 해 봤는지 한 줄과 함께.
