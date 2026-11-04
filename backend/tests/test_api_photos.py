"""사진 읽기 (API-SPEC F1, US-017, US-018). 진짜 AI 대신 가짜 답으로 서버의 검사·규칙표 맞추기·보관을 본다."""
import pytest

from app import ai
from app.db import photo_analyses_repo, rules_repo

CRED = {"email": "kim@example.com", "password": "Passw0rd!"}

JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20


def shape(response):
    body = response.json()
    return response.status_code, body["field"], body["reason"]


def user_id(pg, email=CRED["email"]):
    return str(pg.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()["id"])


def storages(room=None, fridge=None, freezer=None):
    days = {"room": room, "fridge": fridge, "freezer": freezer}
    return [{"storage": s, "allowed": d is not None, "max_days": d} for s, d in days.items()]


def item(name="닭가슴살", recommended="fridge", **kw):
    return {"name": name, "recommended_storage": recommended, "storages": kw.get("storages", storages(fridge=3, freezer=90))}


def upload(client, data=JPG, filename="receipt.jpg", content_type="image/jpeg", field="image"):
    return client.post("/photos/analyze", files={field: (filename, data, content_type)})


@pytest.fixture
def me(client, pg):
    assert client.post("/auth/signup", json=CRED).status_code == 201
    return user_id(pg)


@pytest.fixture
def ai_answer(monkeypatch):
    """AI 가 돌려줄 답을 정하고, AI 가 받은 사진을 기록한다."""
    state = {"answer": {"items": [], "receipt_date": None}, "calls": []}

    def fake(image, media_type):
        state["calls"].append({"image": image, "media_type": media_type})
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(ai, "read_photo", fake)
    return state


def analysis_count(pg):
    return pg.execute("SELECT count(*) AS n FROM photo_analyses").fetchone()["n"]


# ---- 로그인 · 사진 검사 (AI 를 부르기 전에 막는다) -----------------------------------------------
def test_login_required(client, ai_answer):
    assert shape(upload(client)) == (401, None, "login_required")
    assert ai_answer["calls"] == []


def test_missing_photo_is_photo_invalid(client, me, ai_answer):
    assert shape(client.post("/photos/analyze", files={"other": ("a.jpg", JPG, "image/jpeg")})) == (422, "image", "photo_invalid")
    assert shape(client.post("/photos/analyze")) == (422, "image", "photo_invalid")
    assert shape(client.post("/photos/analyze", json={"image": "abc"})) == (422, "image", "photo_invalid")
    assert shape(client.post("/photos/analyze", data={"image": "그냥 글자"})) == (422, "image", "photo_invalid")
    assert ai_answer["calls"] == []


def test_empty_file_is_photo_invalid(client, me, ai_answer):
    assert shape(upload(client, data=b"")) == (422, "image", "photo_invalid")
    assert ai_answer["calls"] == []


def test_two_photos_at_once_is_photo_invalid(client, me, ai_answer):
    response = client.post(
        "/photos/analyze",
        files=[("image", ("a.jpg", JPG, "image/jpeg")), ("image", ("b.png", PNG, "image/png"))],
    )
    assert shape(response) == (422, "image", "photo_invalid") and ai_answer["calls"] == []


@pytest.mark.parametrize(
    "data",
    [b"hello this is not a photo", b"GIF89a" + b"\x00" * 20, b"%PDF-1.7" + b"\x00" * 20, b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 8],
)
def test_other_file_types_are_rejected_even_if_named_like_a_photo(client, me, ai_answer, data):
    assert shape(upload(client, data=data, filename="receipt.jpg", content_type="image/jpeg")) == (422, "image", "photo_invalid")
    assert ai_answer["calls"] == []


def test_a_real_photo_is_accepted_even_if_the_name_or_type_label_is_wrong(client, me, ai_answer):
    assert upload(client, data=PNG, filename="receipt.txt", content_type="text/plain").status_code == 200
    assert ai_answer["calls"][0]["media_type"] == "image/png"  # 이름·표시가 아니라 내용으로 가린다


def test_over_5mb_is_rejected_and_exactly_5mb_is_allowed(client, me, ai_answer):
    five_mb = 5 * 1024 * 1024
    assert shape(upload(client, data=JPG + b"\x00" * (five_mb - len(JPG) + 1))) == (422, "image", "photo_invalid")
    assert ai_answer["calls"] == []
    assert upload(client, data=JPG + b"\x00" * (five_mb - len(JPG))).status_code == 200
    assert len(ai_answer["calls"][0]["image"]) == five_mb


@pytest.mark.parametrize(("data", "media_type"), [(JPG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")])
def test_jpg_png_webp_are_accepted_and_sent_as_they_are(client, me, ai_answer, data, media_type):
    assert upload(client, data=data).status_code == 200
    assert ai_answer["calls"] == [{"image": data, "media_type": media_type}]


# ---- 결과 모양과 보관 ---------------------------------------------------------------------------
def test_returns_items_with_numbers_and_keeps_the_text_result(client, me, pg, ai_answer, today):
    ai_answer["answer"] = {"items": [item("닭가슴살"), item("김치", storages=storages(room=2, fridge=60))], "receipt_date": "2026-10-28"}
    response = upload(client)
    body = response.json()
    assert response.status_code == 200 and set(body) == {"analysis_id", "items"}
    assert body["items"] == [
        {
            "item_no": 0, "name": "닭가슴살", "recommended_storage": "fridge",
            "storages": storages(fridge=3, freezer=90), "purchase_date": "2026-10-28", "from_rule": False,
        },
        {
            "item_no": 1, "name": "김치", "recommended_storage": "fridge",
            "storages": storages(room=2, fridge=60), "purchase_date": "2026-10-28", "from_rule": False,
        },
    ]
    kept = photo_analyses_repo.get_valid_analysis(pg, me, body["analysis_id"])
    assert kept["items"] == body["items"]  # 서버가 글만 30분 보관한다 (D-102)


def test_photo_bytes_are_not_stored_anywhere(client, me, pg, ai_answer):
    marker = b"SECRET-PHOTO-BYTES"
    ai_answer["answer"] = {"items": [item()], "receipt_date": None}
    upload(client, data=JPG + marker)
    dump = pg.execute("SELECT items::text AS t FROM photo_analyses").fetchone()["t"]
    assert "SECRET" not in dump


def test_rule_table_value_wins_when_the_name_is_in_the_rule_table(client, me, ai_answer, pg_rules):
    ai_answer["answer"] = {"items": [item("우유", recommended="freezer", storages=storages(room=99, fridge=99, freezer=99))], "receipt_date": None}
    got = upload(client).json()["items"][0]
    rule = rules_repo.get_rule_by_name(pg_rules, "우유")
    assert got["from_rule"] is True
    assert got["recommended_storage"] == rule["default_storage"] == "fridge"
    assert got["storages"] == rule["storages"]  # AI 값은 버리고 규칙표 값 (D-135)


def test_rule_alias_is_replaced_by_the_official_name(client, me, ai_answer):
    ai_answer["answer"] = {"items": [item("계란")], "receipt_date": None}  # 달걀의 별칭
    got = upload(client).json()["items"][0]
    assert got["name"] == "달걀" and got["from_rule"] is True


def test_unknown_name_keeps_the_ai_values_and_does_not_touch_the_rule_table(client, me, pg_rules, ai_answer):
    ai_answer["answer"] = {"items": [item("닭가슴살")], "receipt_date": None}
    got = upload(client).json()["items"][0]
    assert got["from_rule"] is False and got["storages"] == storages(fridge=3, freezer=90)
    assert rules_repo.get_rule_by_name(pg_rules, "닭가슴살") is None  # 규칙표에 더하는 것은 등록을 확정할 때다 (D-136)
    assert len(rules_repo.list_rules(pg_rules)) == 30


def test_name_is_trimmed_and_matched_exactly(client, me, ai_answer):
    ai_answer["answer"] = {"items": [item("  우유  "), item("우유 1L")], "receipt_date": None}
    items = upload(client).json()["items"]
    assert [(i["name"], i["from_rule"]) for i in items] == [("우유", True), ("우유 1L", False)]  # 띄어쓰기·용량은 보정하지 않는다


# ---- 구매일 -----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("receipt", "expected"),
    [("2026-10-01", "2026-10-01"), ("2026-12-25", "2026-12-25"), (None, "2026-10-30"), ("어제", "2026-10-30"),
     ("2026-02-30", "2026-10-30"), (20261001, "2026-10-30"), ("", "2026-10-30")],
)
def test_purchase_date_is_the_receipt_date_or_today(client, me, ai_answer, receipt, expected):
    ai_answer["answer"] = {"items": [item()], "receipt_date": receipt}
    assert upload(client).json()["items"][0]["purchase_date"] == expected  # 못 읽으면 오늘 (D-107)


# ---- 규칙에 안 맞는 줄은 그 줄만 뺀다 ---------------------------------------------------------------
def bad_items():
    ok = storages(fridge=3, freezer=90)
    return {
        "빈이름": {"name": "  ", "recommended_storage": "fridge", "storages": ok},
        "이름없음": {"recommended_storage": "fridge", "storages": ok},
        "이름숫자": {"name": 5, "recommended_storage": "fridge", "storages": ok},
        "기본불가": {"name": "기본불가", "recommended_storage": "room", "storages": ok},
        "기본이상": {"name": "기본이상", "recommended_storage": "shelf", "storages": ok},
        "일수0": {"name": "일수0", "recommended_storage": "fridge", "storages": storages(fridge=0, freezer=90)},
        "일수음수": {"name": "일수음수", "recommended_storage": "fridge", "storages": storages(fridge=-3, freezer=90)},
        "일수소수": {"name": "일수소수", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": False, "max_days": None}, {"storage": "fridge", "allowed": True, "max_days": 2.5},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "일수글자": {"name": "일수글자", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": False, "max_days": None}, {"storage": "fridge", "allowed": True, "max_days": "7"},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "일수참": {"name": "일수참", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": False, "max_days": None}, {"storage": "fridge", "allowed": True, "max_days": True},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "불가인데일수": {"name": "불가인데일수", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": False, "max_days": 3}, {"storage": "fridge", "allowed": True, "max_days": 3},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "가능인데일수없음": {"name": "가능인데일수없음", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": False, "max_days": None}, {"storage": "fridge", "allowed": True, "max_days": None},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "허용값글자": {"name": "허용값글자", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": "no", "max_days": None}, {"storage": "fridge", "allowed": True, "max_days": 3},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "방법두개": {"name": "방법두개", "recommended_storage": "fridge", "storages": storages(fridge=3, freezer=90)[1:]},
        "방법중복": {"name": "방법중복", "recommended_storage": "fridge", "storages": [
            {"storage": "fridge", "allowed": True, "max_days": 3}, {"storage": "fridge", "allowed": True, "max_days": 3},
            {"storage": "freezer", "allowed": False, "max_days": None}]},
        "방법이상": {"name": "방법이상", "recommended_storage": "fridge", "storages": [
            {"storage": "room", "allowed": False, "max_days": None}, {"storage": "fridge", "allowed": True, "max_days": 3},
            {"storage": "shelf", "allowed": False, "max_days": None}]},
        "방법목록아님": {"name": "방법목록아님", "recommended_storage": "fridge", "storages": "fridge"},
        "줄이문자": "그냥 글",
    }


@pytest.mark.parametrize("label", list(bad_items()))
def test_a_line_that_breaks_the_rules_is_dropped_but_the_rest_stay(client, me, ai_answer, label):
    ai_answer["answer"] = {"items": [item("앞줄"), bad_items()[label], item("뒷줄")], "receipt_date": None}
    response = upload(client)
    assert response.status_code == 200
    assert [i["name"] for i in response.json()["items"]] == ["앞줄", "뒷줄"]
    assert [i["item_no"] for i in response.json()["items"]] == [0, 1]  # 빠진 뒤 번호를 다시 매긴다


def test_all_lines_dropped_is_an_empty_list_not_a_failure(client, me, pg, ai_answer):
    ai_answer["answer"] = {"items": list(bad_items().values()), "receipt_date": None}
    response = upload(client)
    assert response.status_code == 200 and response.json() == {"analysis_id": None, "items": []}
    assert analysis_count(pg) == 0


# ---- 식품을 못 찾았을 때 · 새 사진 · 실패 ---------------------------------------------------------
def test_no_food_found_keeps_nothing_and_leaves_the_previous_result(client, me, pg, ai_answer):
    ai_answer["answer"] = {"items": [item()], "receipt_date": None}
    first = upload(client).json()["analysis_id"]
    ai_answer["answer"] = {"items": [], "receipt_date": None}
    assert upload(client).json() == {"analysis_id": None, "items": []}  # 실패가 아니다 (API-SPEC 5절 24번)
    assert photo_analyses_repo.get_valid_analysis(pg, me, first) is not None  # 이전 결과는 그대로


def test_new_photo_replaces_the_previous_result(client, me, pg, ai_answer):
    ai_answer["answer"] = {"items": [item("첫째")], "receipt_date": None}
    first = upload(client).json()["analysis_id"]
    ai_answer["answer"] = {"items": [item("둘째")], "receipt_date": None}
    second = upload(client).json()["analysis_id"]
    assert first != second and analysis_count(pg) == 1
    assert photo_analyses_repo.get_valid_analysis(pg, me, first) is None  # 이전 사진의 번호는 쓸 수 없다 (Q-29)
    assert photo_analyses_repo.get_valid_analysis(pg, me, second)["items"][0]["name"] == "둘째"


def test_each_account_keeps_its_own_result(client, make_client, me, pg, ai_answer):
    ai_answer["answer"] = {"items": [item("내것")], "receipt_date": None}
    mine = upload(client).json()["analysis_id"]
    other = make_client()
    other.post("/auth/signup", json={"email": "lee@example.com", "password": "Other1234!"})
    ai_answer["answer"] = {"items": [item("남의것")], "receipt_date": None}
    theirs = upload(other).json()["analysis_id"]
    assert analysis_count(pg) == 2
    assert photo_analyses_repo.get_valid_analysis(pg, me, mine) is not None
    assert photo_analyses_repo.get_valid_analysis(pg, me, theirs) is None  # 남의 번호는 없는 것과 같다 (D-063)


def test_ai_failure_is_502_and_keeps_the_previous_result(client, me, pg, ai_answer):
    from app.errors import ApiError

    ai_answer["answer"] = {"items": [item()], "receipt_date": None}
    first = upload(client).json()["analysis_id"]
    ai_answer["answer"] = ApiError("ai_failed")
    response = upload(client)
    assert shape(response) == (502, None, "ai_failed")
    assert response.json()["message"] == "AI 가 응답하지 못했어요. 다시 시도해 주세요."
    assert photo_analyses_repo.get_valid_analysis(pg, me, first) is not None  # 실패하면 이전 줄이 남는다 (Q-31 ⑤)


@pytest.mark.parametrize("answer", [[], "글", {}, {"items": "없음"}, {"items": None}, {"receipt_date": "2026-10-01"}])
def test_malformed_answer_is_ai_failed_and_keeps_the_previous_result(client, me, pg, ai_answer, answer):
    ai_answer["answer"] = {"items": [item()], "receipt_date": None}
    first = upload(client).json()["analysis_id"]
    ai_answer["answer"] = answer
    assert shape(upload(client)) == (502, None, "ai_failed")
    assert photo_analyses_repo.get_valid_analysis(pg, me, first) is not None


def test_nothing_else_is_changed(client, me, pg, ai_answer):
    before = {t: pg.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in ("foods", "rules", "rule_storage", "rule_aliases")}
    ai_answer["answer"] = {"items": [item("닭가슴살"), item("우유")], "receipt_date": None}
    upload(client)
    after = {t: pg.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in before}
    assert after == before  # 식품도 규칙표도 바꾸지 않는다 (D-136)
