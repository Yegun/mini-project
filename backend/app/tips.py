"""오늘의 일반 조언 규칙 (API-SPEC 2-10절 J1, ARCHITECTURE V-38, 3-1, 4-6, D-156 ~ D-158).

하루(한국 시간)에 한 번만 AI 에게 여러 개를 만들게 해 저장하고, 모든 계정이 같은 것을 읽는다. 개인 정보는 AI 에게 보내지 않는다.
AI 가 못 만들거나 맞는 문장이 하나도 안 남으면 저장하지 않고 미리 써 둔 조언을 돌려준다 (사용자에게 실패가 보이지 않는다).
다음 요청에서 다시 만들어 본다. 미리 써 둔 조언은 DB 가 아니라 이 파일에 있다 (DATA-MODEL 6-1).
"""
from datetime import date

from app import ai
from app.errors import ApiError

MAX_TIPS = 10  # 저장하는 조언의 최대 개수. 개수는 구현 단계에서 정한다 (D-156)
MAX_TIP_LENGTH = 120  # 한 문장씩 짧게 (ARCHITECTURE 3-1). 이보다 긴 글은 맞지 않는 문장으로 본다

# 미리 써 둔 조언 (D-157). AI 가 못 만들 때 쓴다. 특정 식품·상표를 광고하지 않는다.
FALLBACK_TIPS = (
    "냉장고는 70% 정도만 채워야 찬 공기가 잘 돌아요.",
    "먼저 산 식품을 앞쪽에, 새로 산 식품을 뒤쪽에 두면 오래된 것부터 먹게 돼요.",
    "냉장고 문 쪽은 온도가 자주 변하니 상하기 쉬운 식품은 안쪽에 두세요.",
    "남은 음식은 식힌 뒤 바로 밀폐 용기에 담아 냉장하세요.",
    "장을 보기 전에 냉장고 속을 한 번 살펴보면 같은 식품을 또 사는 일이 줄어요.",
    "채소는 물기를 닦아 키친타월과 함께 보관하면 더 오래가요.",
    "고기와 생선은 다른 식품과 닿지 않게 따로 담아 두세요.",
    "냉동한 식품에는 날짜를 적어 두면 언제까지 먹을지 잊지 않아요.",
)


def read_tips(answer) -> list[str]:
    """V-38. 모양을 검사하고 맞는 문장만 남긴다. 모양이 틀리거나 하나도 안 남으면 ai_failed.

    맞는 문장: 비어 있지 않은 글이고 너무 길지 않다. 같은 문장은 한 번만 남기고, MAX_TIPS 개까지만 쓴다.
    """
    if not isinstance(answer, dict) or not isinstance(answer.get("tips"), list):
        raise ApiError("ai_failed")
    tips: list[str] = []
    for text in answer["tips"]:
        if not isinstance(text, str):
            continue
        text = text.strip()
        if text and len(text) <= MAX_TIP_LENGTH and text not in tips:
            tips.append(text)
    if not tips:
        raise ApiError("ai_failed")
    return tips[:MAX_TIPS]


def make_tips() -> list[str] | None:
    """AI 에게 오늘의 조언을 만들게 한다. 못 만들면 None (부르는 쪽이 미리 써 둔 조언으로 대신한다, D-157)."""
    try:
        return read_tips(ai.make_tips())
    except ApiError:
        return None


def body(tip_date: date, tips: list[str], *, from_ai: bool) -> dict:
    """J1 응답 모양. 저장된 조언은 모두 AI 가 만든 것이라 from_ai 가 참이고, 미리 써 둔 조언은 거짓이다."""
    return {"tip_date": tip_date.isoformat(), "tips": [{"text": text, "from_ai": from_ai} for text in tips]}


def fallback_body(tip_date: date) -> dict:
    return body(tip_date, list(FALLBACK_TIPS), from_ai=False)
