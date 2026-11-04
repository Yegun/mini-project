"""음식 추천 (API-SPEC G1, US-021). 진짜 AI 대신 가짜 답으로 서버의 검사·정렬·표시를 본다."""
import pytest

from app import ai
from app.db import foods_repo
from app.errors import ApiError
from tests.conftest import food_args

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}
GOOD = {"meal": "dinner", "cuisine": "korean"}


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


def user_id(pg, email=CRED["email"]):
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])


def add(pg, uid, name, expiry, **over):
    foods_repo.create_food(pg, uid, **food_args(name=name, purchase_date="2026-10-20", expiry_date=expiry, **over))


@pytest.fixture
def me(client, pg):
    assert client.post("/auth/signup", json=CRED).status_code == 201
    return user_id(pg)


@pytest.fixture
def stocked(me, pg):
    """오늘은 2026-10-30. 달걀(1일 남음), 양파(20일), 우유(지남), 두부(처리함)."""
    add(pg, me, "달걀", "2026-10-31")
    add(pg, me, "양파", "2026-11-19")
    add(pg, me, "우유", "2026-10-29")
    done = foods_repo.create_food(pg, me, **food_args(name="두부", purchase_date="2026-10-20", expiry_date="2026-11-20"))
    foods_repo.set_status(pg, me, done["id"], "eaten", "2026-10-30")
    pg.commit()
    return me


@pytest.fixture
def ai_answer(monkeypatch):
    """AI 가 돌려줄 답을 정하고, AI 가 받은 자료를 기록한다."""
    state = {"answer": {"dishes": []}, "calls": []}

    def fake(foods, meal, cuisine, cuisine_text):
        state["calls"].append({"foods": foods, "meal": meal, "cuisine": cuisine, "cuisine_text": cuisine_text})
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(ai, "suggest_dishes", fake)
    return state


def dish(name, *ingredients):
    return {"name": name, "ingredients": list(ingredients)}


def post(client, **body):
    return client.post("/recommendations", json=body)


# ---- 로그인 · 입력 검사 -------------------------------------------------------------------------
def test_login_required(client, ai_answer):
    response = post(client, **GOOD)
    assert shape(response) == (401, None, "login_required") and ai_answer["calls"] == []


@pytest.mark.parametrize("meal", [None, "", "brunch", "Dinner", 1, ["dinner"]])
def test_invalid_meal(client, me, ai_answer, meal):
    assert shape(post(client, meal=meal, cuisine="korean")) == (422, "meal", "invalid_meal")
    assert ai_answer["calls"] == []


@pytest.mark.parametrize("cuisine", [None, "", "thai", 3])
def test_invalid_cuisine(client, me, ai_answer, cuisine):
    assert shape(post(client, meal="dinner", cuisine=cuisine)) == (422, "cuisine", "invalid_cuisine")
    assert ai_answer["calls"] == []


@pytest.mark.parametrize("text", [None, "", "   ", "가" * 31, 5])
def test_custom_cuisine_needs_text_up_to_30_chars(client, me, ai_answer, text):
    response = post(client, meal="dinner", cuisine="custom", cuisine_text=text)
    assert shape(response) == (422, "cuisine_text", "invalid_cuisine_text") and ai_answer["calls"] == []


def test_custom_text_of_30_chars_is_allowed_and_trimmed(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("달걀양파볶음", "달걀", "양파")]}
    response = post(client, meal="lunch", cuisine="custom", cuisine_text="  " + "가" * 30 + "  ")
    assert response.status_code == 200
    assert ai_answer["calls"][0]["cuisine_text"] == "가" * 30


def test_text_is_ignored_unless_custom(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("달걀양파볶음", "달걀", "양파")]}
    assert post(client, meal="dinner", cuisine="korean", cuisine_text="가" * 99).status_code == 200
    assert ai_answer["calls"][0]["cuisine_text"] is None  # AI 에게도 보내지 않는다


def test_input_is_checked_before_foods_and_ai(client, me, ai_answer):
    # 식품이 없어도 입력 오류가 먼저다 (확인 순서: 입력 검사 → 식품 읽기)
    assert shape(post(client, meal="x", cuisine="korean"))[2] == "invalid_meal"


# ---- 재료로 쓸 식품 ---------------------------------------------------------------------------
def test_no_foods_returns_empty_without_calling_ai(client, me, ai_answer):
    response = post(client, **GOOD)
    assert response.status_code == 200 and response.json() == {"dishes": [], "reason": "no_foods"}
    assert ai_answer["calls"] == []


def test_only_unprocessed_not_expired_foods_go_to_ai(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("달걀양파볶음", "달걀", "양파")]}
    post(client, **GOOD)
    assert ai_answer["calls"][0]["foods"] == [
        {"name": "달걀", "days_left": 1},
        {"name": "양파", "days_left": 20},
    ]  # 우유(지남)·두부(처리함)는 빠지고 수량·구매일·계정 번호는 가지 않는다 (D-120, D-126)


def test_only_expired_foods_means_no_foods(client, me, pg, ai_answer):
    add(pg, me, "우유", "2026-10-29")
    pg.commit()
    assert post(client, **GOOD).json() == {"dishes": [], "reason": "no_foods"}
    assert ai_answer["calls"] == []


def test_expiry_day_itself_is_still_usable(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-10-30")  # 기한 당일 = 남은 날 0
    add(pg, me, "양파", "2026-11-19")
    pg.commit()
    ai_answer["answer"] = {"dishes": [dish("달걀양파볶음", "달걀", "양파")]}
    assert post(client, **GOOD).json()["dishes"]
    assert {"name": "달걀", "days_left": 0} in ai_answer["calls"][0]["foods"]


def test_other_accounts_foods_are_never_sent(client, make_client, stocked, pg, ai_answer):
    other = make_client()
    other.post("/auth/signup", json={"email": "lee@example.com", "password": "Other1234!"})
    add(pg, user_id(pg, "lee@example.com"), "사과", "2026-11-10")
    pg.commit()
    ai_answer["answer"] = {"dishes": []}
    post(client, **GOOD)
    assert "사과" not in [f["name"] for f in ai_answer["calls"][0]["foods"]]


# ---- AI 답 검사 ------------------------------------------------------------------------------
def test_shows_name_and_ingredients_with_have_flags_and_no_recipe(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("달걀양파볶음", "달걀", "양파", "참기름")], "recipe": "볶는다"}
    response = post(client, **GOOD)
    assert response.json() == {
        "dishes": [
            {
                "name": "달걀양파볶음",
                "ingredients": [
                    {"name": "달걀", "have": True},
                    {"name": "양파", "have": True},
                    {"name": "참기름", "have": False},
                ],
            }
        ],
        "reason": None,
    }


def test_drops_dishes_with_fewer_than_two_owned_ingredients(client, stocked, ai_answer):
    ai_answer["answer"] = {
        "dishes": [
            dish("계란찜", "달걀", "물", "소금"),  # 가진 재료 1개
            dish("양파수프", "양파", "양파", "버터"),  # 같은 식품을 두 번 써도 1개로 센다
            dish("우유죽", "우유", "쌀"),  # 지난 식품은 내 재료가 아니다
            dish("달걀양파볶음", "달걀", "양파"),
        ]
    }
    assert [d["name"] for d in post(client, **GOOD).json()["dishes"]] == ["달걀양파볶음"]


def test_ownership_is_decided_by_exact_name(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("계란양파", "계란", "양파", "대파")]}  # '계란' 은 내 식품 '달걀' 과 글자가 다르다
    assert post(client, **GOOD).json() == {"dishes": [], "reason": "no_match"}


def test_no_match_when_nothing_survives(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("김치찌개", "김치", "돼지고기")]}
    response = post(client, **GOOD)
    assert response.status_code == 200 and response.json() == {"dishes": [], "reason": "no_match"}


def test_empty_answer_is_no_match(client, stocked, ai_answer):
    ai_answer["answer"] = {"dishes": []}
    assert post(client, **GOOD).json() == {"dishes": [], "reason": "no_match"}


def test_at_most_three_dishes(client, me, pg, ai_answer):
    for name in ("달걀", "양파", "두부", "대파"):
        add(pg, me, name, "2026-11-19")
    pg.commit()
    ai_answer["answer"] = {"dishes": [dish(f"음식{n}", "달걀", "양파") for n in range(5)]}
    assert [d["name"] for d in post(client, **GOOD).json()["dishes"]] == ["음식0", "음식1", "음식2"]


def test_dishes_using_the_soonest_expiring_food_come_first(client, me, pg, ai_answer):
    add(pg, me, "버섯", "2026-11-25")  # 26일
    add(pg, me, "양파", "2026-11-19")  # 20일
    add(pg, me, "달걀", "2026-10-31")  # 1일
    add(pg, me, "두부", "2026-11-04")  # 5일
    pg.commit()
    ai_answer["answer"] = {
        "dishes": [
            dish("버섯양파덮밥", "버섯", "양파"),  # 가장 급한 재료 20일
            dish("두부버섯조림", "두부", "버섯"),  # 5일
            dish("달걀양파볶음", "달걀", "양파"),  # 1일
            dish("두부양파국", "두부", "양파"),  # 5일 (두부버섯조림과 같으면 AI 순서)
        ]
    }
    names = [d["name"] for d in post(client, **GOOD).json()["dishes"]]
    assert names == ["달걀양파볶음", "두부버섯조림", "두부양파국"]


def test_same_name_foods_use_the_soonest_one(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-11-25")
    add(pg, me, "달걀", "2026-10-31")  # 같은 이름을 여러 번 샀다 (D-030)
    add(pg, me, "양파", "2026-11-19")
    pg.commit()
    ai_answer["answer"] = {"dishes": [dish("느린음식", "양파", "대파", "버섯"), dish("달걀양파볶음", "달걀", "양파")]}
    # 달걀은 1일 남은 것이 기준이라 앞에 온다 (느린음식은 가진 재료가 양파 1개라 빠진다)
    assert [d["name"] for d in post(client, **GOOD).json()["dishes"]] == ["달걀양파볶음"]


# ---- AI 가 잘못 답했을 때 ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "answer",
    [
        [],
        "그냥 글",
        {"dishes": "없음"},
        {},
        {"dishes": [{"ingredients": ["달걀", "양파"]}]},  # 이름이 없다
        {"dishes": [{"name": "음식", "ingredients": "달걀, 양파"}]},  # 재료가 목록이 아니다
        {"dishes": [{"name": "음식", "ingredients": ["달걀", 3]}]},
        {"dishes": [{"name": "  ", "ingredients": ["달걀", "양파"]}]},
        {"dishes": ["음식"]},
    ],
)
def test_malformed_answer_is_ai_failed(client, stocked, ai_answer, answer):
    ai_answer["answer"] = answer
    assert shape(post(client, **GOOD)) == (502, None, "ai_failed")


def test_ai_failure_is_502(client, stocked, ai_answer):
    ai_answer["answer"] = ApiError("ai_failed")
    response = post(client, **GOOD)
    assert shape(response) == (502, None, "ai_failed")
    assert response.json()["message"] == "AI 가 응답하지 못했어요. 다시 시도해 주세요."


def test_asking_again_gives_a_new_answer_and_saves_nothing(client, stocked, pg, ai_answer):
    ai_answer["answer"] = {"dishes": [dish("첫음식", "달걀", "양파")]}
    assert post(client, **GOOD).json()["dishes"][0]["name"] == "첫음식"
    ai_answer["answer"] = {"dishes": [dish("둘째음식", "달걀", "양파")]}
    assert post(client, **GOOD).json()["dishes"][0]["name"] == "둘째음식"  # 횟수 제한 없음 (D-123)
    tables = [r["table_name"] for r in pg.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")]
    assert not [t for t in tables if "recommend" in t or "dish" in t]  # 추천 결과를 저장할 표가 없다 (D-122)
    assert pg.execute("SELECT count(*) AS n FROM photo_analyses").fetchone()["n"] == 0


def test_foods_are_not_changed(client, stocked, pg, ai_answer):
    before = pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"]
    ai_answer["answer"] = {"dishes": [dish("달걀양파볶음", "달걀", "양파")]}
    post(client, **GOOD)
    assert pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"] == before
