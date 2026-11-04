"""사진 읽기 규칙 (API-SPEC 2-5절 F1, ARCHITECTURE V-23, V-26, D-101 ~ D-107, D-135).

사진은 메모리에만 두고 AI 에게 보낸 뒤 버린다. 저장하는 것은 읽은 결과(글)뿐이다 (D-102).
AI 의 답은 믿지 않고 서버가 검사한다. 규칙에 안 맞는 줄은 그 줄만 빼고 (ARCHITECTURE 3-1), 규칙표에 같은 이름이 있으면
AI 값을 버리고 규칙표 값으로 바꾼다 (D-135). 위험 여부·이유·종류도 같다 (D-190, D-191).
"""
from datetime import date

import psycopg

from app import ai
from app.db import photo_analyses_repo, rules_repo
from app.errors import ApiError
from app.validation import CATEGORIES, ValidationError

PHOTO_MAX_BYTES = 5 * 1024 * 1024  # 5MB (D-101)
STORAGES = ("room", "fridge", "freezer")


def sniff_media_type(data: bytes) -> str | None:
    """파일 내용의 첫 바이트로 jpg · png · webp 인지 가린다. 이름이나 보낸 형식 표시는 믿지 않는다."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def check_photo(parts: list[bytes] | None) -> tuple[bytes, str]:
    """V-23. 사진은 한 번에 한 장, 형식은 jpg · png · webp, 크기는 5MB 이하. 어기면 AI 를 부르지 않고 photo_invalid.

    parts 는 보낸 image 칸의 파일 내용들이다 (없으면 None 이나 빈 목록).
    """
    if not parts or len(parts) != 1 or not parts[0] or len(parts[0]) > PHOTO_MAX_BYTES:
        raise ValidationError("image", "photo_invalid")
    media_type = sniff_media_type(parts[0])
    if media_type is None:
        raise ValidationError("image", "photo_invalid")
    return parts[0], media_type


def _positive_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _clean_item(raw) -> dict | None:
    """AI 가 준 한 줄이 규칙(V-26)에 맞으면 {"name", "recommended_storage", "storages"} 를, 아니면 None 을 돌려준다.

    규칙: 이름이 있고, 보관 방법 세 가지가 한 번씩 있고, 가능한 방법은 최대 일수가 0보다 큰 정수, 불가는 비어 있고,
    권장 보관 방법은 가능한 방법이다. 그리고 위험 여부(danger)는 참 또는 거짓이어야 하고, 위험이면 이유 한 줄이
    비어 있지 않아야 한다 (V-36). 위험 여부가 없거나 알아볼 수 없으면 그 줄을 뺀다 (D-191).
    종류(category)는 다섯 값 중 하나다. 알아볼 수 없으면 other 로 둔다.
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str) or not raw["name"].strip():
        return None
    listed = raw.get("storages")
    if not isinstance(listed, list) or len(listed) != len(STORAGES):
        return None
    by_storage = {}
    for info in listed:
        if not isinstance(info, dict) or info.get("storage") not in STORAGES or info["storage"] in by_storage:
            return None
        allowed, max_days = info.get("allowed"), info.get("max_days")
        if not isinstance(allowed, bool) or (allowed and not _positive_int(max_days)) or (not allowed and max_days is not None):
            return None
        by_storage[info["storage"]] = {"storage": info["storage"], "allowed": allowed, "max_days": max_days}
    recommended = raw.get("recommended_storage")
    if recommended not in STORAGES or not by_storage[recommended]["allowed"]:
        return None
    danger = raw.get("danger")
    if not isinstance(danger, bool):
        return None  # 위험 여부가 없거나 알아볼 수 없다 (V-36)
    note = raw.get("danger_note")
    if danger:
        if not isinstance(note, str) or not note.strip():
            return None  # 위험인데 이유 한 줄이 없다 (V-36)
        note = note.strip()
    else:
        note = None  # 위험이 아니면 이유는 비운다
    category = raw.get("category")
    return {
        "name": raw["name"].strip(),
        "recommended_storage": recommended,
        "storages": [by_storage[s] for s in STORAGES],  # 상온 · 냉장 · 냉동 순
        "is_danger": danger,
        "danger_note": note,
        "category": category if category in CATEGORIES else "other",
    }


def _receipt_date(value, today: date) -> str:
    """영수증에서 읽은 날짜. 못 읽었거나 날짜가 아니면 오늘이다 (D-106, D-107)."""
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()).isoformat()
        except ValueError:
            pass
    return today.isoformat()


def build_items(conn: psycopg.Connection, answer, today: date) -> list[dict]:
    """AI 답을 검사하고 규칙표와 맞춰 확인 화면에 줄 목록을 만든다 (저장은 하지 않는다).

    답 모양이 틀리면 ai_failed 다. 일부 줄만 규칙에 안 맞으면 그 줄만 뺀다.
    이름이 규칙표에 있으면(이름 또는 별칭이 글자 그대로 같을 때) AI 값을 버리고 규칙표 값을 쓴다 (D-135).
    AI 가 준 칸 이름 danger 는 응답에서 is_danger 로 바꿔 돌려준다 (API-SPEC 5절 49번).
    """
    if not isinstance(answer, dict) or not isinstance(answer.get("items"), list):
        raise ApiError("ai_failed")
    purchase_date = _receipt_date(answer.get("receipt_date"), today)
    items = []
    for raw in answer["items"]:
        item = _clean_item(raw)
        if item is None:
            continue
        rule = rules_repo.find_rule(conn, item["name"])
        if rule is not None:
            item = {
                "name": rule["name"],
                "recommended_storage": rule["default_storage"],
                "storages": [dict(info) for info in rule["storages"]],
                # 위험 여부·이유·종류도 AI 값을 버리고 규칙표 값을 쓴다 (D-190, D-191)
                "is_danger": rule["is_danger"],
                "danger_note": rule["danger_note"] if rule["is_danger"] else None,
                "category": rule["category"],
            }
        items.append(
            {
                "item_no": len(items),
                "name": item["name"],
                "recommended_storage": item["recommended_storage"],
                "storages": item["storages"],
                "purchase_date": purchase_date,
                "from_rule": rule is not None,
                "is_danger": item["is_danger"],
                "danger_note": item["danger_note"],
                "category": item["category"],
            }
        )
    return items


def analyze(conn: psycopg.Connection, user_id: str, image: bytes, media_type: str, today: date) -> dict:
    """F1. 사진을 AI 에게 읽히고 결과(글)를 내 계정으로 30분 보관한다. 식품이 하나도 없으면 보관하지 않는다.

    DB 쓰기는 AI 답을 받은 뒤에 한 묶음으로 한다 (부르는 쪽이 transaction 으로 감싼다).
    """
    answer = ai.read_photo(image, media_type)
    items = build_items(conn, answer, today)
    if not items:
        return {"analysis_id": None, "items": []}  # 실패가 아니다. 이전 결과는 그대로 둔다
    return {"analysis_id": photo_analyses_repo.save_analysis(conn, user_id, items), "items": items}
