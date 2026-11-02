# DEV-ENVIRONMENT — 개발 환경 기록

> 표준 경로: 화면 React · Vite / API FastAPI / 저장소 SQLite ([ARCHITECTURE.md](ARCHITECTURE.md))
> 확인일: 2026-10-28. 아래 버전은 `--version` 실행 결과를 그대로 적었다.

## 운영체제 · 셸

| 항목 | 값 |
|---|---|
| 운영체제 | Microsoft Windows 11 Pro (10.0.22631) |
| 셸 | PowerShell 7.6.7 (Git Bash도 사용 가능) |

## 도구별 버전

| 도구 | 명령 | 결과 |
|---|---|---|
| git | `git --version` | `git version 2.56.0.windows.2` |
| node | `node --version` | `v22.23.3` |
| npm | `npm --version` | `10.9.9` |
| uv | `uv --version` | `uv 0.13.1 (62faed335 2026-10-13 x86_64-pc-windows-msvc)` |
| python | `python3.12 --version` (uv 설치본) | `Python 3.12.15` |

- ⚠️ 그냥 `python --version` 은 `Python` 만 나온다. 윈도우 스토어 안내용 가짜 실행 파일(`C:\Users\EZ\AppData\Local\Microsoft\WindowsApps\python.exe`)이 먼저 잡히기 때문이다. 실제 Python 은 uv 가 설치한 3.12.15 이며 `uv run python` 으로 쓴다.
- `py`, `pip`, `pnpm`, `yarn`, `sqlite3` 명령줄은 없다. 지금 단계에서는 필요 없다.
- SQLite 는 Python 에 내장된 `sqlite3` 모듈을 쓴다. (버전은 확인 전)

## 새로 설치한 것

없음. 위 도구는 모두 이미 설치되어 있던 것이다.

아직 설치하지 않은 것(승인 후 설치 예정): FastAPI, Uvicorn, pytest, httpx, React · Vite 프로젝트.
