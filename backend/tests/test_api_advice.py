"""기록 조언 (API-SPEC I1, US-034). 진짜 AI 대신 가짜 답으로 서버의 자료 만들기·모양 검사·빈 결과를 본다."""
import json

import pytest

from app import advice, ai
from app.db import foods_repo
from app.errors import ApiError
from tests.conftest import food_args

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


def user_id(pg, email=CRED["email"]):
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])


def add(pg, uid, name, expiry, **over):
    return foods_repo.create_food(
        pg, uid, **food_args(name=name, purchase_date="2026-10-20", expiry_date=expiry, quantity=7, unit="봉지", **over)
    )


def process(pg, uid, food, status, on):
    foods_repo.set_status(pg, uid, food["id"], status, on)


@pytest.fixture
def me(client, pg):
    assert client.post("/auth/signup", json=CRED).status_code == 201
    return user_id(pg)


@pytest.fixture
def ai_answer(monkeypatch):
    """AI 가 돌려줄 답을 정하고, AI 가 받은 자료를 기록한다."""
    state = {"answer": {"advice": ["먼저 산 달걀부터 먹어요."]}, "calls": []}

    def fake(material):
        state["calls"].append(material)
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(ai, "give_advice", fake)
    return state


# ---- 로그인 · 빈 결과 ---------------------------------------------------------------------------------
def test_login_required(make_client, ai_answer):
    assert shape(make_client().post("/advice")) == (401, None, "login_required")
    assert ai_answer["calls"] == []


def test_no_foods_and_no_records_returns_no_data_without_calling_ai(client, me, ai_answer):
    response = client.post("/advice")
    assert response.status_code == 200 and response.json() == {"advice": [], "reason": "no_data"}  # 실패가 아니다
    assert ai_answer["calls"] == []  # V-37


def test_only_other_accounts_foods_still_means_no_data(client, make_client, me, pg, ai_answer):
    other = make_client()
    other.post("/auth/signup", json={"email": "lee@example.com", "password": "Other1234!"})
    add(pg, user_id(pg, "lee@example.com"), "달걀", "2026-11-05")
    pg.commit()
    assert client.post("/advice").json() == {"advice": [], "reason": "no_data"}
    assert ai_answer["calls"] == []


# ---- AI 에 보내는 자료 -------------------------------------------------------------------------------
def test_current_foods_alone_are_enough_to_get_advice(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-10-31")  # 오늘 2026-10-30, 1일 남음
    pg.commit()
    response = client.post("/advice")
    assert response.status_code == 200 and response.json() == {"advice": ["먼저 산 달걀부터 먹어요."], "reason": None}
    assert ai_answer["calls"] == [{"active": [{"name": "달걀", "status": "soon", "days_left": 1}], "processed": []}]


def test_records_alone_are_enough_to_get_advice(client, me, pg, ai_answer):
    done = add(pg, me, "우유", "2026-10-20")
    process(pg, me, done, "discarded", "2026-10-29")
    pg.commit()
    assert client.post("/advice").status_code == 200
    assert ai_answer["calls"] == [
        {"active": [], "processed": [
            {"name": "우유", "result": "discarded", "processed_date": "2026-10-29", "expiry_date": "2026-10-20"}]}
    ]


def test_material_has_states_days_and_processed_details_in_the_documented_shape(client, me, pg, ai_answer):
    for name, expiry in [("지남", "2026-10-28"), ("임박", "2026-11-01"), ("주의", "2026-11-04"), ("여유", "2026-11-20")]:
        add(pg, me, name, expiry)
    eaten = add(pg, me, "다먹음", "2026-11-10")
    thrown = add(pg, me, "버림", "2026-10-25")
    process(pg, me, eaten, "eaten", "2026-10-28")
    process(pg, me, thrown, "discarded", "2026-10-29")
    pg.commit()
    client.post("/advice")
    sent = ai_answer["calls"][0]
    assert {f["name"]: (f["status"], f["days_left"]) for f in sent["active"]} == {
        "지남": ("expired", -2), "임박": ("soon", 2), "주의": ("warning", 5), "여유": ("fresh", 21)}
    assert [(f["name"], f["result"], f["processed_date"], f["expiry_date"]) for f in sent["processed"]] == [
        ("버림", "discarded", "2026-10-29", "2026-10-25"), ("다먹음", "eaten", "2026-10-28", "2026-11-10")]  # 최근 처리한 순


def test_expired_foods_are_included_in_the_advice_material(client, me, pg, ai_answer):
    add(pg, me, "지난식품", "2026-10-20")
    pg.commit()
    client.post("/advice")
    assert ai_answer["calls"][0]["active"] == [{"name": "지난식품", "status": "expired", "days_left": -10}]


def test_no_email_account_quantity_or_purchase_date_is_sent(client, me, pg, ai_answer):
    food = add(pg, me, "달걀", "2026-10-31")
    done = add(pg, me, "우유", "2026-10-25")
    process(pg, me, done, "eaten", "2026-10-29")
    pg.commit()
    client.post("/advice")
    text = json.dumps(ai_answer["calls"][0], ensure_ascii=False)
    for secret in ("kim@example.com", me, food["id"], done["id"], "봉지", "2026-10-20", "quantity", "purchase", "email"):
        assert secret not in text, secret  # D-163


def test_other_accounts_foods_are_never_sent(client, make_client, me, pg, ai_answer):
    other = make_client()
    other.post("/auth/signup", json={"email": "lee@example.com", "password": "Other1234!"})
    lee = user_id(pg, "lee@example.com")
    add(pg, me, "내식품", "2026-11-05")
    add(pg, lee, "남의식품", "2026-11-05")
    gone = add(pg, lee, "남의기록", "2026-11-05")
    process(pg, lee, gone, "discarded", "2026-10-29")
    pg.commit()
    client.post("/advice")
    assert [f["name"] for f in ai_answer["calls"][0]["active"]] == ["내식품"]
    assert ai_answer["calls"][0]["processed"] == []


def test_only_the_latest_processed_foods_up_to_the_limit_are_sent(client, me, pg, ai_answer, monkeypatch):
    monkeypatch.setattr(advice, "PROCESSED_LIMIT", 3)
    for index, day in enumerate(["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"]):
        food = add(pg, me, f"식품{index}", "2026-11-05")
        process(pg, me, food, "eaten", day)
    pg.commit()
    client.post("/advice")
    assert [f["name"] for f in ai_answer["calls"][0]["processed"]] == ["식품4", "식품3", "식품2"]


def test_the_limit_is_a_hundred_foods(client):
    assert advice.PROCESSED_LIMIT == 100


# ---- AI 답 검사 · 실패 ---------------------------------------------------------------------------------
def test_advice_sentences_are_trimmed_and_returned_in_order(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-10-31")
    pg.commit()
    ai_answer["answer"] = {"advice": ["  첫째 조언  ", "둘째 조언"]}
    assert client.post("/advice").json() == {"advice": ["첫째 조언", "둘째 조언"], "reason": None}


@pytest.mark.parametrize(
    "answer",
    [None, "글", [], {}, {"advice": None}, {"advice": "글"}, {"advice": []}, {"advice": [1]}, {"advice": ["좋아요", ""]},
     {"advice": ["좋아요", "  "]}, {"advice": [["중첩"]]}, {"tips": ["다른 칸"]}],
)
def test_a_malformed_answer_is_ai_failed(client, me, pg, ai_answer, answer):
    add(pg, me, "달걀", "2026-10-31")
    pg.commit()
    ai_answer["answer"] = answer
    assert shape(client.post("/advice")) == (502, None, "ai_failed")


def test_ai_failure_is_502_with_the_documented_message(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-10-31")
    pg.commit()
    ai_answer["answer"] = ApiError("ai_failed")
    response = client.post("/advice")
    assert shape(response) == (502, None, "ai_failed")
    assert response.json()["message"] == "AI 가 응답하지 못했어요. 다시 시도해 주세요."


def test_nothing_is_saved_and_asking_again_gives_new_advice(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-10-31")
    pg.commit()
    before = pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"]
    first = client.post("/advice").json()
    ai_answer["answer"] = {"advice": ["다른 조언"]}
    second = client.post("/advice").json()
    assert first != second and len(ai_answer["calls"]) == 2  # 횟수 제한 없이 매번 새로 묻는다 (D-161)
    assert pg.execute("SELECT count(*) AS n FROM foods").fetchone()["n"] == before
    assert pg.execute("SELECT count(*) AS n FROM daily_tips").fetchone()["n"] == 0  # 조언은 저장하지 않는다


def test_a_body_is_not_needed_and_extra_fields_are_ignored(client, me, pg, ai_answer):
    add(pg, me, "달걀", "2026-10-31")
    pg.commit()
    assert client.post("/advice", json={"anything": 1}).status_code == 200
