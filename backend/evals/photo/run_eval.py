"""사진 읽기 지시문 평가 실행기.

app/ai.py 가 쓰는 것과 같은 호출(같은 사진 블록, 같은 사용자 문장, 같은 옵션)에서 지시문(system)만 바꿔 가며
labels.json 의 영수증을 읽히고 채점한다. 앱 코드는 바꾸지 않는다.

사용 (backend 폴더에서)
  python -m evals.photo.run_eval --selfcheck                        채점기 점검 (호출 없음, 비용 없음)
  python -m evals.photo.run_eval --variants current,v1 --dry-run    계획과 예상 비용만 (호출 없음)
  python -m evals.photo.run_eval --variants current,v1 --reps 3     실제 호출 (돈이 든다)

지시문 후보는 evals/photo/prompts/<이름>.txt 이다. 'current' 는 지금 app/ai.py 의 PHOTO_SYSTEM 이다.
결과는 evals/photo/runs/<이름>/ 에 줄마다 바로 저장되고, 같은 (지시문, 영수증, 번호)는 다시 부르지 않는다.
영수증 사진은 evals/photo/receipts/ 에만 두고 Git 에 올리지 않는다.
"""
import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app import ai
from app.photo import check_photo
from evals.photo.grade import grade, missing_and_extra, receipt_dates

HERE = Path(__file__).resolve().parent
RECEIPTS = HERE / "receipts"
PROMPTS = HERE / "prompts"
RUNS = HERE / "runs"
METRICS = ["f1", "recall", "precision", "rule_match", "date_ok", "valid_rate"]
# 100만 토큰당 가격 (달러). claude-api 안내서의 현재 모델 표
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00), "claude-opus-5-5": (4.00, 20.00)}
USER_TEXT = "이 사진에서 냉장·냉동 보관이 필요한 식품을 읽어 줘."  # app/ai.py 의 read_photo 와 같은 문장


def load_labels() -> dict:
    return json.loads((HERE / "labels.json").read_text(encoding="utf-8"))["receipts"]


def load_prompt(name: str) -> str:
    if name == "current":
        return ai.PHOTO_SYSTEM
    return (PROMPTS / f"{name}.txt").read_text(encoding="utf-8").rstrip("\n")


def cost_usd(model: str, usage: dict) -> float:
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    return (usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1_000_000


def call_ai(system: str, image: bytes, media_type: str, model: str, effort: str) -> dict:
    """한 번 호출하고 원답과 사용량을 돌려준다. 자동 재시도는 없다 (앱과 같다)."""
    import base64

    started = time.time()
    response = ai._client(ai.PHOTO_TIMEOUT_SECONDS).messages.create(
        model=model,
        max_tokens=ai.PHOTO_MAX_TOKENS,
        system=system,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                         "data": base64.standard_b64encode(image).decode("ascii")}},
            {"type": "text", "text": USER_TEXT},
        ]}],
    )
    if response.model != model:  # 요청한 모델이 아닌 것으로 대체됐으면 비교가 깨진다
        raise RuntimeError(f"서버가 다른 모델로 답했다: {response.model}")
    return {
        "text": "".join(b.text for b in response.content if b.type == "text"),
        "stop_reason": response.stop_reason,
        "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
        "model": response.model,
        "latency_s": round(time.time() - started, 2),
    }


def read_done(path: Path) -> set:
    if not path.exists():
        return set()
    return {(r["receipt"], r["rep"]) for r in map(json.loads, path.read_text(encoding="utf-8").splitlines() if path.stat().st_size else [])}


def run_case(variant: str, system: str, receipt_id: str, receipt: dict, rep: int, model: str, effort: str, out: Path) -> dict | None:
    image, media_type = check_photo([(RECEIPTS / receipt["file"]).read_bytes()])
    try:
        raw = call_ai(system, image, media_type, model, effort)
    except Exception as error:  # 호출 자체가 실패했다 (시간 초과·연결·AI 오류). 점수에 넣지 않고 따로 적는다
        with (out / "errors.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"receipt": receipt_id, "rep": rep, "class": type(error).__name__}, ensure_ascii=False) + "\n")
        return None
    status, answer = "ok", None
    if raw["stop_reason"] in ("refusal", "max_tokens"):
        status = raw["stop_reason"]
    else:
        try:
            answer = ai._json_from(raw["text"])
        except Exception:
            status = "bad_json"  # 앱에서는 ai_failed 가 되는 답이다
    scores = grade(answer, receipt)
    row = {
        "variant": variant, "receipt": receipt_id, "rep": rep, "status": status, "grade": scores,
        **missing_and_extra(answer, receipt),
        "date_read": answer.get("receipt_date") if isinstance(answer, dict) else None,
        "names": [i["name"] for i in (answer.get("items", []) if isinstance(answer, dict) else []) if isinstance(i, dict) and isinstance(i.get("name"), str)],
        "model": raw["model"], "effort": effort, "usage": raw["usage"], "latency_s": raw["latency_s"],
        "cost_usd": round(cost_usd(raw["model"], raw["usage"]), 6),
    }
    with (out / "results.jsonl").open("a", encoding="utf-8") as f:  # 끝나는 대로 바로 쓴다
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["status"] == "ok"]
    out = {"n": len(rows), "ok": len(ok), "cost": round(sum(r["cost_usd"] for r in rows), 4),
           "latency": round(statistics.mean(r["latency_s"] for r in rows), 1) if rows else 0.0}
    for m in METRICS:
        out[m] = round(statistics.mean(r["grade"][m] for r in rows), 3) if rows else 0.0
    return out


def print_summary(names: list[str]) -> None:
    print("| 지시문 | 호출 | f1 | recall | precision | rule_match | date_ok | valid_rate | 평균 시간 | 비용 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name in names:
        path = RUNS / name / "results.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        s = summarize(rows)
        print(f"| {name} | {s['n']} | {s['f1']} | {s['recall']} | {s['precision']} | {s['rule_match']} | {s['date_ok']} | "
              f"{s['valid_rate']} | {s['latency']}초 | ${s['cost']} |")


def selfcheck() -> int:
    """채점기가 맞는지 호출 없이 확인한다: 정답을 그대로 내면 만점, 빈 답은 0점, 엉뚱한 답은 정밀도 0."""
    labels = load_labels()
    ok = True

    def storages(**days):
        return [{"storage": s, "allowed": days.get(s) is not None, "max_days": days.get(s)} for s in ("room", "fridge", "freezer")]

    for rid, receipt in labels.items():
        oracle = {"items": [{"name": e["prefer"], "recommended_storage": "fridge", "storages": storages(fridge=5)}
                            for e in receipt["expected"]], "receipt_date": receipt_dates(receipt)[0]}
        null_empty = {"items": [], "receipt_date": None}
        junk = {"items": [{"name": "라면", "recommended_storage": "room", "storages": storages(room=9)}], "receipt_date": "1999-01-01"}
        broken = {"items": [{"name": e["prefer"]} for e in receipt["expected"]], "receipt_date": receipt_dates(receipt)[0]}
        cases = [
            ("정답 그대로", oracle, {"f1": 1.0, "recall": 1.0, "precision": 1.0, "rule_match": 1.0, "date_ok": 1.0, "valid_rate": 1.0}),
            ("빈 답", null_empty, {"f1": 0.0, "recall": 0.0, "precision": 0.0}),  # 날짜가 없음이 정답인 사진은 date_ok 가 1 일 수 있다
            ("엉뚱한 답", junk, {"f1": 0.0, "recall": 0.0, "precision": 0.0, "date_ok": 0.0}),
            ("글이 아닌 답", "그냥 글", {"f1": 0.0, "recall": 0.0, "precision": 0.0, "date_ok": 0.0}),
            ("형식이 틀린 줄(서버가 버림)", broken, {"recall": 1.0, "valid_rate": 0.0}),
        ]
        for label, answer, expect in cases:
            got = grade(answer, receipt)
            bad = {k: (got[k], v) for k, v in expect.items() if got[k] != v}
            ok &= not bad
            print(("OK  " if not bad else "FAIL"), rid, label, bad if bad else "")
    print("채점기 점검:", "통과" if ok else "실패")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--variants", default="current", help="쉼표로 구분한 지시문 이름 (current 는 지금 앱의 지시문)")
    parser.add_argument("--reps", type=int, default=3, help="영수증마다 반복할 횟수")
    parser.add_argument("--model", default=ai.DEFAULT_MODEL)
    parser.add_argument("--effort", default="low")
    parser.add_argument("--receipts", default="", help="쉼표로 구분한 영수증 번호만 돌린다 (예: r06). 비우면 전부")
    parser.add_argument("--holdout", action="store_true", help="정답표에 holdout 으로 표시된 처음 보는 영수증만 돌린다")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true", help="호출하지 않고 계획과 예상 비용만 보인다")
    parser.add_argument("--selfcheck", action="store_true", help="채점기를 호출 없이 점검한다")
    parser.add_argument("--summary", action="store_true", help="저장된 결과만 표로 보인다")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()
    names = [v.strip() for v in args.variants.split(",") if v.strip()]
    if args.summary:
        print_summary(names)
        return 0
    labels = load_labels()
    if args.receipts:
        wanted = {r.strip() for r in args.receipts.split(",")}
        labels = {k: v for k, v in labels.items() if k in wanted}
    if args.holdout:
        labels = {k: v for k, v in labels.items() if v.get("holdout")}
    missing_files = [r["file"] for r in labels.values() if not (RECEIPTS / r["file"]).exists()]
    if missing_files:
        print("사진이 없다:", missing_files)
        return 2

    jobs = []
    for name in names:
        system = load_prompt(name)
        out = RUNS / name
        out.mkdir(parents=True, exist_ok=True)
        done = read_done(out / "results.jsonl")
        for rid, receipt in labels.items():
            for rep in range(args.reps):
                if (rid, rep) not in done:
                    jobs.append((name, system, rid, receipt, rep, out))

    price_in, price_out = PRICES.get(args.model, (0, 0))
    estimate = len(jobs) * (2100 * price_in + 1400 * price_out) / 1_000_000  # 앞서 잰 값: 입력 약 2,100 · 출력 약 1,400 토큰
    print(f"모델 {args.model} / effort {args.effort} / 지시문 {names} / 영수증 {len(labels)}장 × {args.reps}번")
    print(f"새로 부를 호출 {len(jobs)}번 (이미 끝난 것은 건너뜀), 예상 비용 약 ${estimate:.3f}")
    if args.dry_run or not jobs:
        print_summary(names)
        return 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_case, n, s, rid, r, rep, args.model, args.effort, out) for n, s, rid, r, rep, out in jobs]
        for done_count, future in enumerate(as_completed(futures), 1):
            row = future.result()
            print(f"  {done_count}/{len(jobs)}", "실패(errors.jsonl)" if row is None else f"{row['variant']} {row['receipt']}#{row['rep']} f1={row['grade']['f1']} {row['status']}", flush=True)
    print()
    print_summary(names)
    return 0


if __name__ == "__main__":
    sys.exit(main())
