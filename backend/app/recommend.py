"""음식 추천 규칙 (API-SPEC 2-6절 G1, ARCHITECTURE V-27, V-28, D-113 ~ D-123).

AI 의 답을 믿지 않고 서버가 검사한다. 내 식품인지는 서버가 이름으로 직접 정한다 (ARCHITECTURE 3-1).
결과는 저장하지 않는다 (D-122).
"""
from datetime import date

from app import ai
from app.errors import ApiError
from app.status import days_left
from app.validation import ValidationError

MEALS = ("breakfast", "lunch", "dinner")
CUISINES = ("western", "korean", "japanese", "chinese", "simple", "custom")
CUISINE_TEXT_MAX = 30  # API-SPEC 5절 22번
MAX_DISHES = 3  # D-113
MIN_OWNED_INGREDIENTS = 2  # D-119


def validate_request(raw: dict) -> tuple[str, str, str | None]:
    """V-27. 끼니 하나, 음식 종류 하나가 필수이고 '직접 입력'이면 글자가 필수다 (30자까지).

    cuisine 이 custom 이 아닌데 cuisine_text 가 오면 무시한다 (API-SPEC 5절 35번).
    """
    meal, cuisine = raw["meal"], raw["cuisine"]
    if not isinstance(meal, str) or meal not in MEALS:
        raise ValidationError("meal", "invalid_meal")
    if not isinstance(cuisine, str) or cuisine not in CUISINES:
        raise ValidationError("cuisine", "invalid_cuisine")
    if cuisine != "custom":
        return meal, cuisine, None
    text = raw["cuisine_text"]
    text = text.strip() if isinstance(text, str) else ""
    if not text or len(text) > CUISINE_TEXT_MAX:
        raise ValidationError("cuisine_text", "invalid_cuisine_text")
    return meal, cuisine, text


def usable_foods(foods: list[dict], today: date) -> list[dict]:
    """재료로 쓸 식품: 처리 전이고 지남이 아닌 것의 이름과 남은 날 (V-28, D-120). 입력은 처리 전 식품 목록이다."""
    result = []
    for food in foods:
        left = days_left(date.fromisoformat(food["expiry_date"]), today)
        if left >= 0:
            result.append({"name": food["name"], "days_left": left})
    return result


def _read_dishes(answer) -> list[tuple[str, list[str]]]:
    """AI 답의 모양을 검사한다. 맞지 않으면 ai_failed (V-30)."""
    if not isinstance(answer, dict) or not isinstance(answer.get("dishes"), list):
        raise ApiError("ai_failed")
    dishes = []
    for dish in answer["dishes"]:
        if not isinstance(dish, dict) or not isinstance(dish.get("name"), str) or not dish["name"].strip():
            raise ApiError("ai_failed")
        ingredients = dish.get("ingredients")
        if not isinstance(ingredients, list) or not all(isinstance(i, str) and i.strip() for i in ingredients):
            raise ApiError("ai_failed")
        dishes.append((dish["name"].strip(), [i.strip() for i in ingredients]))
    return dishes


def choose_dishes(answer, foods: list[dict]) -> list[dict]:
    """AI 답에서 규칙에 맞는 음식만 남긴다 (V-28).

    - 내 식품이 재료로 2개 이상(서로 다른 식품) 들어가는 음식만 (D-119). 가진 식품은 이름이 글자 그대로 같을 때다.
    - 기한이 임박한 식품을 먼저 쓰는 음식이 앞에 온다 (D-114). 같으면 AI 가 준 순서 그대로다.
    - 3개 이하로 자른다 (D-113). 재료마다 가진 것인지 표시한다 (D-115). 만드는 법은 없다 (D-121).
    """
    days_by_name: dict[str, int] = {}
    for food in foods:
        days_by_name[food["name"]] = min(food["days_left"], days_by_name.get(food["name"], food["days_left"]))

    kept = []
    for position, (name, ingredients) in enumerate(_read_dishes(answer)):
        owned = {i for i in ingredients if i in days_by_name}
        if len(owned) < MIN_OWNED_INGREDIENTS:
            continue
        urgency = min(days_by_name[i] for i in owned)  # 남은 날이 가장 적은 가진 재료
        shown = [{"name": i, "have": i in days_by_name} for i in dict.fromkeys(ingredients)]
        kept.append((urgency, position, {"name": name, "ingredients": shown}))
    kept.sort(key=lambda item: (item[0], item[1]))
    return [dish for _, _, dish in kept[:MAX_DISHES]]


def recommend(raw: dict, active_foods: list[dict], today: date) -> dict:
    """G1. active_foods 는 내 식품 중 처리 전인 것이다. 가진 식품이 없으면 AI 를 부르지 않는다 (no_foods)."""
    meal, cuisine, cuisine_text = validate_request(raw)
    foods = usable_foods(active_foods, today)
    if not foods:
        return {"dishes": [], "reason": "no_foods"}
    dishes = choose_dishes(ai.suggest_dishes(foods, meal, cuisine, cuisine_text), foods)
    return {"dishes": dishes, "reason": None if dishes else "no_match"}
