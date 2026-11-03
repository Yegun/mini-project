"""사진 읽기 채점 (프로그램으로 계산한다. 사람이 쓴 정답표 labels.json 과 AI 의 답을 비교한다).

정답표의 optional(넣어도 빼도 되는 품목)에 해당하는 AI 줄은 점수에 넣지 않는다.
점수는 한 숫자로 합치지 않고 따로 낸다. 대표 점수(primary)는 f1 이다.
  recall     등록되어야 할 식품 중 AI 가 읽은 비율 (빠지지 않고 다 읽기)
  precision  AI 가 읽은 줄 중 정답에 있는 비율 (식품이 아닌 것을 넣지 않기)
  f1         recall 과 precision 의 조화평균 (대표 점수)
  rule_match 읽은 정답 식품 중 이름이 prefer(규칙표와 맞는 이름)와 같은 비율
  date_ok    영수증 날짜를 정답표의 날짜들(receipt_dates, null 은 '날짜 없음') 중 하나로 읽었으면 1
  valid_rate AI 가 준 줄 중 서버 규칙(V-26)을 통과하는 줄의 비율 (서버가 버리는 줄이 없는지)
"""
from app.photo import _clean_item


def _items(answer) -> list:
    if isinstance(answer, dict) and isinstance(answer.get("items"), list):
        return answer["items"]
    return []


def receipt_dates(receipt: dict) -> list:
    """맞는 영수증 날짜들. 글씨가 여러 형식으로 읽히거나 날짜가 없는 사진은 여러 값(null 포함)을 인정한다."""
    return receipt.get("receipt_dates", [receipt.get("receipt_date")])


def grade(answer, receipt: dict) -> dict:
    """answer 는 AI 가 준 JSON(dict), receipt 는 labels.json 의 한 영수증. 점수 dict 를 돌려준다."""
    items = _items(answer)
    all_names = [i["name"].strip() for i in items if isinstance(i, dict) and isinstance(i.get("name"), str)]
    optional = {n for o in receipt.get("optional", []) for n in o["accept"]}
    names = [n for n in all_names if n not in optional]  # 넣어도 빼도 되는 품목은 점수에서 뺀다
    expected = receipt["expected"]

    matched, used = [], set()  # 정답 식품마다 맞는 AI 줄 하나를 찾는다 (한 줄은 한 정답에만 쓴다)
    for exp in expected:
        k = next((k for k, n in enumerate(names) if k not in used and n in exp["accept"]), None)
        if k is not None:
            used.add(k)
            matched.append((exp, names[k]))
    matched_count = len(matched)

    recall = matched_count / len(expected) if expected else 1.0
    precision = matched_count / len(names) if names else (1.0 if not expected else 0.0)
    f1 = 0.0 if recall + precision == 0 else 2 * recall * precision / (recall + precision)
    rule_match = (sum(1 for exp, hit in matched if hit == exp["prefer"]) / matched_count) if matched_count else 0.0
    valid_rate = (sum(1 for i in items if _clean_item(i)) / len(items)) if items else 1.0
    date_ok = 1.0 if isinstance(answer, dict) and answer.get("receipt_date") in receipt_dates(receipt) else 0.0
    return {
        "f1": round(f1, 4), "recall": round(recall, 4), "precision": round(precision, 4),
        "rule_match": round(rule_match, 4), "date_ok": date_ok, "valid_rate": round(valid_rate, 4),
    }


def missing_and_extra(answer, receipt: dict) -> dict:
    """사람이 읽기 쉬운 설명: 빠진 정답 식품과 정답에 없는 줄 (이름만)."""
    names = [i["name"].strip() for i in _items(answer) if isinstance(i, dict) and isinstance(i.get("name"), str)]
    accepted = {n for exp in receipt["expected"] for n in exp["accept"]} | {n for o in receipt.get("optional", []) for n in o["accept"]}
    missing = [exp["label"] for exp in receipt["expected"] if not any(n in exp["accept"] for n in names)]
    extra = [n for n in names if n not in accepted]
    return {"missing": missing, "extra": extra}
