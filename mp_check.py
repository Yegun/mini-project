"""구현 시작 전 점검. 표준 라이브러리만 쓰고 파일은 읽기만 한다.

실행: python mp_check.py
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOC_NAMES = ["TEAM", "PRD", "ARCHITECTURE", "SCREEN-SPEC", "DATA-MODEL",
             "API-SPEC", "DECISIONS", "AGENTS", "PLAN"]
SKIP_DIRS = {"node_modules", ".venv", ".git", "__pycache__"}
PREFIX = re.compile(r"^v(\d+)\.(\d+)\.(\d+)_")

results = []  # (통과 여부, 한 줄 메시지)


def report(ok, label, detail=""):
    tag = "[통과]" if ok else "[수정 필요]"
    results.append(ok)
    print(f"{tag} {label}" + (f" — {detail}" if detail else ""))


def read(path):
    return path.read_text(encoding="utf-8-sig", errors="replace")


def find_doc(name):
    """루트와 docs/ 아래에서 이름이 맞는 파일을 찾는다. 같은 이름이면 높은 버전."""
    best, best_key = None, None
    for base in (ROOT, ROOT / "docs"):
        files = base.rglob("*.md") if base.name == "docs" else base.glob("*.md")
        for p in files:
            if SKIP_DIRS & set(p.parts):
                continue
            m = PREFIX.match(p.name)
            stem = p.stem
            ver = (0, 0, 0)
            if m:
                ver = tuple(int(x) for x in m.groups())
                stem = p.name[m.end():-len(".md")]
            if stem != name:
                continue
            key = (ver, base == ROOT)
            if best_key is None or key > best_key:
                best, best_key = p, key
    return best


def section(text, title_word, level=2):
    """제목에 title_word 가 든 절의 본문(같은 단계 이상 제목 전까지)."""
    lines = text.splitlines()
    head = re.compile(rf"^#{{1,{level}}}\s")
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^#{{{level}}}\s", ln) and title_word in ln:
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if head.match(lines[j]):
            end = j
            break
    return lines[start:end]


def table_rows(lines):
    """표의 본문 행(머리글·구분선 제외)을 칸 목록으로."""
    rows = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows[1:]  # 첫 행은 머리글


def check_docs():
    missing, found = [], {}
    for n in DOC_NAMES:
        p = find_doc(n)
        if p is None:
            missing.append(n + ".md")
        else:
            found[n] = p
    problems = []
    if missing:
        problems.append("없음: " + ", ".join(missing))
    for n in ("PRD", "ARCHITECTURE"):
        if n in found:
            first = next((l for l in read(found[n]).splitlines() if l.strip()), "")
            if not re.search(r"상태\s*[:：]\s*확정", first):
                problems.append(f"{n} 맨 위가 「상태: 확정」이 아님(현재: {first.strip()[:30]})")
    report(not problems, "1. 문서 아홉 · 상태 확정", "; ".join(problems))
    return found


def check_must(prd):
    if prd is None:
        return report(False, "2. PRD 범위의 Must", "PRD.md 없음")
    sec = section(read(prd), "범위")
    if sec is None:
        return report(False, "2. PRD 범위의 Must", "「범위」 절 없음")
    start = next((i for i, l in enumerate(sec) if re.match(r"^#{3,}\s", l) and "Must" in l), None)
    if start is None:
        return report(False, "2. PRD 범위의 Must", "Must 항목 제목 없음")
    end = next((j for j in range(start + 1, len(sec)) if re.match(r"^#{1,3}\s", sec[j])), len(sec))
    rows = table_rows(sec[start + 1:end])
    if not rows:
        return report(False, "2. PRD 범위의 Must", "Must 표에 항목 없음")
    if any(not c for r in rows for c in r):
        return report(False, "2. PRD 범위의 Must", "Must 표에 빈 칸 있음")
    report(True, "2. PRD 범위의 Must", f"{len(rows)}개")


def check_us(prd):
    if prd is None:
        return report(False, "3. PRD 사용자 스토리 완료 조건", "PRD.md 없음")
    sec = section(read(prd), "사용자 스토리")
    if sec is None:
        return report(False, "3. PRD 사용자 스토리 완료 조건", "「사용자 스토리」 절 없음")
    blocks = re.split(r"(?m)^###\s+(?=US-)", "\n".join(sec))[1:]
    if not blocks:
        return report(False, "3. PRD 사용자 스토리 완료 조건", "US 없음")
    bad = []
    for b in blocks:
        lines = b.splitlines()
        rows = table_rows(lines[1:])
        ok = bool(rows) and all(len(r) >= 3 and all(r[:3]) for r in rows)
        if not ok:
            bad.append(lines[0].split("·")[0].strip())
    report(not bad, "3. PRD 사용자 스토리 완료 조건",
           ("부족: " + ", ".join(bad)) if bad else f"US {len(blocks)}개 모두 상황·행동·결과 있음")


def check_decisions_env(decisions):
    if decisions is None:
        report(False, "4-1. DECISIONS 결정 3개 이상", "DECISIONS.md 없음")
    else:
        n = len(re.findall(r"(?m)^##\s+D-\d+", read(decisions)))
        report(n >= 3, "4-1. DECISIONS 결정 3개 이상", f"{n}개")
    gi = ROOT / ".gitignore"
    ok = gi.is_file() and any(l.strip() == ".env" for l in read(gi).splitlines())
    report(ok, "4-2. .gitignore 에 .env", "" if ok else ".gitignore 에 .env 줄 없음")


def version_of(cmd):
    exe = shutil.which(cmd[0])
    if not exe:
        return None, "설치 안 됨"
    try:
        out = subprocess.run([exe] + cmd[1:], capture_output=True, text=True,
                             errors="replace", timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"실행 실패({e.__class__.__name__})"
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out.stdout + out.stderr)
    if not m:
        return None, "버전을 읽지 못함"
    return tuple(int(x) for x in m.groups(default="0")), m.group(0)


def check_tools():
    specs = [("node", ["node", "-v"], (20,)),
             ("Python", [sys.executable, "--version"], (3, 12)),
             ("uv", ["uv", "--version"], None),
             ("git", ["git", "--version"], None),
             ("psql", ["psql", "--version"], (16,))]
    for label, cmd, minimum in specs:
        ver, text = version_of(cmd)
        if ver is None:
            report(False, f"5. {label}", text)
        elif minimum and ver[:len(minimum)] < minimum:
            need = ".".join(map(str, minimum))
            report(False, f"5. {label}", f"{text} (필요: {need} 이상)")
        else:
            report(True, f"5. {label}", text)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    found = check_docs()
    check_must(found.get("PRD"))
    check_us(found.get("PRD"))
    check_decisions_env(found.get("DECISIONS"))
    check_tools()
    n = results.count(False)
    print(f"수정 필요 {n}개" if n else "구현을 시작할 수 있습니다")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
