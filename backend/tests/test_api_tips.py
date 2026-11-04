"""오늘의 일반 조언 (API-SPEC J1, US-033, US-043). 진짜 AI 대신 가짜 답으로 하루 한 번 만들기·저장·미리 써 둔 조언을 본다."""
import pytest

from app import ai, tips
from app.db import tips_repo
from app.errors import ApiError

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}
OTHER = {"email": "lee@example.com", "password": "Other1234!"}


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


@pytest.fixture
def me(client):
    assert client.post("/auth/signup", json=CRED).status_code == 201


@pytest.fixture
def ai_answer(monkeypatch):
    """AI 가 돌려줄 답을 정하고, AI 를 몇 번 불렀는지 센다."""
    state = {"answer": {"tips": ["냉장고는 70%만 채워요.", "남은 음식은 식혀서 넣어요."]}, "calls": 0}

    def fake():
        state["calls"] += 1
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(ai, "make_tips", fake)
    return state


def texts(response):
    return [t["text"] for t in response.json()["tips"]]


# ---- 로그인 ----------------------------------------------------------------------------------------
def test_login_required(make_client, ai_answer):
    assert shape(make_client().get("/tips")) == (401, None, "login_required")
    assert ai_answer["calls"] == 0


# ---- 오늘 것이 없으면 만들어 저장한다 -------------------------------------------------------------------
def test_first_request_of_the_day_asks_ai_and_saves_the_tips(client, me, pg, ai_answer, today):
    response = client.get("/tips")
    assert response.status_code == 200
    assert response.json() == {
        "tip_date": "2026-10-30",
        "tips": [{"text": "냉장고는 70%만 채워요.", "from_ai": True}, {"text": "남은 음식은 식혀서 넣어요.", "from_ai": True}],
    }
    assert ai_answer["calls"] == 1
    assert tips_repo.get_tips(pg, today) == ["냉장고는 70%만 채워요.", "남은 음식은 식혀서 넣어요."]


def test_second_request_of_the_same_day_reads_the_saved_tips_without_calling_ai(client, me, ai_answer):
    first = client.get("/tips").json()
    second = client.get("/tips").json()
    assert first == second and ai_answer["calls"] == 1  # V-38 하루에 한 번만 AI 를 부른다


def test_all_accounts_read_the_same_tips(client, make_client, me, ai_answer):
    other = make_client()
    other.post("/auth/signup", json=OTHER)
    first, second = client.get("/tips").json(), other.get("/tips").json()
    assert first == second and ai_answer["calls"] == 1  # 계정마다 AI 를 부르지 않는다 (D-156)


def test_a_new_day_makes_new_tips(client, me, pg, ai_answer, monkeypatch):
    from datetime import date

    from app.database import get_today
    from app.main import app

    client.get("/tips")
    app.dependency_overrides[get_today] = lambda: date(2026, 10, 31)  # 한국 시간으로 하루가 지났다
    ai_answer["answer"] = {"tips": ["새 날의 조언"]}
    body = client.get("/tips").json()
    assert body["tip_date"] == "2026-10-31" and [t["text"] for t in body["tips"]] == ["새 날의 조언"]
    assert pg.execute("SELECT count(*) AS n FROM daily_tips").fetchone()["n"] == 2  # 오래된 날짜는 지우지 않는다
    assert ai_answer["calls"] == 2


def test_saved_tips_are_always_from_ai(client, me, ai_answer):
    client.get("/tips")
    assert {t["from_ai"] for t in client.get("/tips").json()["tips"]} == {True}


def test_nothing_personal_is_needed_for_making_tips(client, me, ai_answer):
    # make_tips 는 인자를 받지 않는다. 개인 정보를 보낼 길이 없다 (D-156)
    import inspect

    assert not inspect.signature(ai.make_tips).parameters


# ---- AI 답 검사 --------------------------------------------------------------------------------------
def test_only_valid_sentences_are_kept_trimmed_and_deduplicated(client, me, pg, ai_answer, today):
    ai_answer["answer"] = {"tips": ["  좋은 조언  ", "", "   ", 3, None, ["x"], "좋은 조언", "또 다른 조언", "가" * 121]}
    assert texts(client.get("/tips")) == ["좋은 조언", "또 다른 조언"]
    assert tips_repo.get_tips(pg, today) == ["좋은 조언", "또 다른 조언"]


def test_a_sentence_of_exactly_the_maximum_length_is_kept(client, me, ai_answer):
    ai_answer["answer"] = {"tips": ["가" * tips.MAX_TIP_LENGTH]}
    assert texts(client.get("/tips")) == ["가" * tips.MAX_TIP_LENGTH]


def test_at_most_ten_tips_are_kept(client, me, pg, ai_answer, today):
    ai_answer["answer"] = {"tips": [f"조언 {n}" for n in range(15)]}
    assert texts(client.get("/tips")) == [f"조언 {n}" for n in range(10)]
    assert len(tips_repo.get_tips(pg, today)) == 10


# ---- 못 만들면 미리 써 둔 조언 (저장하지 않는다) -------------------------------------------------------------
@pytest.mark.parametrize(
    "answer",
    [ApiError("ai_failed"), None, "글", [], {}, {"tips": None}, {"tips": "글"}, {"tips": []}, {"tips": [1, 2]},
     {"tips": ["", "  "]}, {"tips": ["가" * 500]}, {"advice": ["다른 칸"]}],
)
def test_when_ai_cannot_make_tips_the_prepared_tips_are_returned_and_nothing_is_saved(client, me, pg, ai_answer, answer):
    ai_answer["answer"] = answer
    response = client.get("/tips")
    assert response.status_code == 200  # ai_failed 를 주지 않는다 (D-157)
    body = response.json()
    assert body["tip_date"] == "2026-10-30"
    assert [t["text"] for t in body["tips"]] == list(tips.FALLBACK_TIPS)
    assert {t["from_ai"] for t in body["tips"]} == {False}  # 미리 써 둔 것은 거짓
    assert pg.execute("SELECT count(*) AS n FROM daily_tips").fetchone()["n"] == 0


def test_the_next_request_tries_again_after_a_failure(client, me, pg, ai_answer):
    ai_answer["answer"] = ApiError("ai_failed")
    assert {t["from_ai"] for t in client.get("/tips").json()["tips"]} == {False}
    ai_answer["answer"] = {"tips": ["이번에는 성공"]}
    assert client.get("/tips").json()["tips"] == [{"text": "이번에는 성공", "from_ai": True}]
    assert ai_answer["calls"] == 2
    assert {t["from_ai"] for t in client.get("/tips").json()["tips"]} == {True}  # 이제 저장돼 있다
    assert ai_answer["calls"] == 2


def test_prepared_tips_are_in_the_code_not_the_database(pg):
    assert len(tips.FALLBACK_TIPS) >= 5 and len(set(tips.FALLBACK_TIPS)) == len(tips.FALLBACK_TIPS)
    assert all(text.strip() and len(text) <= tips.MAX_TIP_LENGTH for text in tips.FALLBACK_TIPS)
    assert pg.execute("SELECT count(*) AS n FROM daily_tips").fetchone()["n"] == 0


# ---- 같은 날 동시에 만들 때 ----------------------------------------------------------------------------
def test_when_another_request_saved_first_that_one_stays_and_is_returned(client, me, pg, ai_answer, today, monkeypatch):
    # 이 요청이 AI 를 기다리는 사이 다른 요청이 먼저 오늘 줄을 저장했다. 먼저 저장된 줄이 남고 이 요청은 그것을 돌려준다
    def slow_then_other_saves():
        tips_repo.add_tips(pg, today, ["먼저 저장된 조언"])
        pg.commit()
        return {"tips": ["나중에 만든 조언"]}

    monkeypatch.setattr(ai, "make_tips", slow_then_other_saves)
    assert client.get("/tips").json()["tips"] == [{"text": "먼저 저장된 조언", "from_ai": True}]
    assert tips_repo.get_tips(pg, today) == ["먼저 저장된 조언"]


# ---- 저장소 ----------------------------------------------------------------------------------------
def test_repo_adds_one_row_per_day_and_never_overwrites(pg, today):
    assert tips_repo.get_tips(pg, today) is None
    assert tips_repo.add_tips(pg, today, ["첫째"]) is True
    assert tips_repo.add_tips(pg, today, ["둘째"]) is False  # 먼저 저장된 것이 남는다
    assert tips_repo.get_tips(pg, today) == ["첫째"]


def test_repo_does_not_commit_by_itself(pg, today):
    tips_repo.add_tips(pg, today, ["첫째"])
    pg.rollback()
    assert tips_repo.get_tips(pg, today) is None


def test_repo_keeps_korean_text_and_order(pg, today):
    tips_repo.add_tips(pg, today, ["하나", "둘", "셋"])
    pg.commit()
    assert tips_repo.get_tips(pg, today) == ["하나", "둘", "셋"]
