"""식품 저장소 (PostgreSQL). 계정 분리, 처리·되돌리기, DB 가 막는 규칙을 본다. 임시 schema 만 쓴다."""
import uuid

import psycopg
import pytest
from conftest import food_args

from app.db.foods_repo import (
    create_food,
    delete_food,
    get_food,
    list_active_foods,
    list_processed_foods,
    restore_food,
    set_status,
    update_food,
)
from app.db.users_repo import create_user


def test_create_then_read_same_values(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args(quantity=0.25))
    assert len(food["id"]) == 36
    assert food["status"] == "none" and food["processed_date"] is None
    assert food["quantity"] == 0.25
    assert food["purchase_date"] == "2026-10-30"  # 날짜는 YYYY-MM-DD 글자
    assert get_food(pg, a["id"], food["id"]) == food


def test_same_name_can_be_registered_many_times(pg, two_users):
    a, _ = two_users
    first = create_food(pg, a["id"], **food_args())
    second = create_food(pg, a["id"], **food_args())
    assert first["id"] != second["id"]
    assert len(list_active_foods(pg, a["id"])) == 2


def test_other_account_sees_nothing(pg, two_users):
    a, b = two_users
    food = create_food(pg, a["id"], **food_args())
    assert list_active_foods(pg, b["id"]) == []
    assert get_food(pg, b["id"], food["id"]) is None  # 남의 식품 = 없는 식품 (D-063)
    assert get_food(pg, b["id"], food["id"], include_processed=True) is None
    assert update_food(pg, b["id"], food["id"], name="대파") is None
    assert set_status(pg, b["id"], food["id"], "eaten", "2026-11-02") is None
    assert delete_food(pg, b["id"], food["id"]) is False
    assert get_food(pg, a["id"], food["id"])["name"] == "양파"  # 주인 것은 그대로


def test_missing_and_malformed_id_are_same_as_not_found(pg, two_users):
    a, _ = two_users
    for bad in (str(uuid.uuid4()), "abc", "", "123"):
        assert get_food(pg, a["id"], bad) is None
        assert update_food(pg, a["id"], bad, name="x") is None
        assert set_status(pg, a["id"], bad, "eaten", "2026-11-02") is None
        assert restore_food(pg, a["id"], bad) is None
        assert delete_food(pg, a["id"], bad) is False


def test_list_order_expiry_then_purchase_then_name(pg, two_users):
    a, _ = two_users
    create_food(pg, a["id"], **food_args(name="나", expiry_date="2026-11-10", purchase_date="2026-11-01"))
    create_food(pg, a["id"], **food_args(name="가", expiry_date="2026-11-10", purchase_date="2026-11-01"))
    create_food(pg, a["id"], **food_args(name="다", expiry_date="2026-11-10", purchase_date="2026-10-01"))
    create_food(pg, a["id"], **food_args(name="라", expiry_date="2026-11-05", purchase_date="2026-11-04"))
    assert [f["name"] for f in list_active_foods(pg, a["id"])] == ["라", "다", "가", "나"]


def test_name_order_is_by_character_code(pg, two_users):
    """이름순은 글자 코드 순이다 (Q-23): 한글은 가나다, 영문은 대문자가 소문자보다 앞."""
    a, _ = two_users
    for name in ("b", "B", "나", "가", "a"):
        create_food(pg, a["id"], **food_args(name=name))
    assert [f["name"] for f in list_active_foods(pg, a["id"])] == ["B", "a", "b", "가", "나"]


def test_update_only_given_fields(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    updated = update_food(pg, a["id"], food["id"], quantity=3.5, unit="봉", purchase_date="2026-10-31")
    assert (updated["quantity"], updated["unit"], updated["purchase_date"]) == (3.5, "봉", "2026-10-31")
    assert (updated["name"], updated["expiry_date"]) == ("양파", "2026-11-29")
    assert update_food(pg, a["id"], food["id"]) == updated  # 고칠 칸이 없으면 그대로


def test_update_rejects_unknown_fields(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    for field in ("id", "status", "processed_date"):  # user_id 는 인자 중복으로 파이썬이 먼저 막는다
        with pytest.raises(ValueError):
            update_food(pg, a["id"], food["id"], **{field: "x"})


def test_process_saves_date_and_hides_from_home(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    done = set_status(pg, a["id"], food["id"], "eaten", "2026-11-02")
    assert (done["status"], done["processed_date"]) == ("eaten", "2026-11-02")
    assert list_active_foods(pg, a["id"]) == []
    # 처리된 식품은 홈·상세에서 없는 식품과 같다 (D-091)
    assert get_food(pg, a["id"], food["id"]) is None
    assert get_food(pg, a["id"], food["id"], include_processed=True)["status"] == "eaten"
    assert update_food(pg, a["id"], food["id"], name="대파") is None
    assert delete_food(pg, a["id"], food["id"]) is False
    assert set_status(pg, a["id"], food["id"], "discarded", "2026-11-02") is None  # 재처리 불가


def test_set_status_rejects_other_values(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    with pytest.raises(ValueError):
        set_status(pg, a["id"], food["id"], "none", "2026-11-02")


def test_restore_keeps_everything_but_status_and_date(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args(expiry_date="2026-10-31"))  # 기한이 지난 식품
    set_status(pg, a["id"], food["id"], "discarded", "2026-11-02")
    back = restore_food(pg, a["id"], food["id"])
    assert back == food  # 처리 전과 똑같다 (D-076)
    assert [f["id"] for f in list_active_foods(pg, a["id"])] == [food["id"]]
    assert restore_food(pg, a["id"], food["id"]) is None  # 처리되지 않은 식품은 없는 것처럼


def test_restore_other_account_is_not_found(pg, two_users):
    a, b = two_users
    food = create_food(pg, a["id"], **food_args())
    set_status(pg, a["id"], food["id"], "eaten", "2026-11-02")
    assert restore_food(pg, b["id"], food["id"]) is None
    assert get_food(pg, a["id"], food["id"], include_processed=True)["status"] == "eaten"


def test_delete_removes_row(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    assert delete_food(pg, a["id"], food["id"]) is True
    assert get_food(pg, a["id"], food["id"], include_processed=True) is None
    assert delete_food(pg, a["id"], food["id"]) is False


def test_processed_list_split_and_order(pg, two_users):
    a, b = two_users
    ids = {}
    for name, status, day in [
        ("가", "eaten", "2026-11-01"), ("나", "eaten", "2026-11-02"), ("다", "eaten", "2026-11-02"),
        ("라", "discarded", "2026-10-15"),
    ]:
        ids[name] = create_food(pg, a["id"], **food_args(name=name))["id"]
        set_status(pg, a["id"], ids[name], status, day)
    create_food(pg, a["id"], **food_args(name="마"))  # 처리 안 함 → 나오지 않는다
    other = create_food(pg, b["id"], **food_args(name="남"))
    set_status(pg, b["id"], other["id"], "eaten", "2026-11-02")  # 남의 식품 → 나오지 않는다

    result = list_processed_foods(pg, a["id"])
    assert [f["name"] for f in result["eaten"]] == ["나", "다", "가"]  # 최근 처리한 순, 같으면 이름순
    assert [f["name"] for f in result["discarded"]] == ["라"]
    assert set(result["eaten"][0]) == {"id", "name", "quantity", "unit", "processed_date"}


def test_processed_list_empty(pg, two_users):
    a, _ = two_users
    assert list_processed_foods(pg, a["id"]) == {"eaten": [], "discarded": []}


# ---- DB 가 막는 규칙 (Q-08) -----------------------------------------------------------------
@pytest.mark.parametrize(
    "over",
    [
        dict(quantity=0),
        dict(quantity=-1),
        dict(quantity=100000000),  # 정수 8자리 초과 (Q-05)
        dict(name="   "),
        dict(unit=""),
        dict(storage="shelf"),
        dict(source="auto"),
        dict(purchase_date="2026-12-01", expiry_date="2026-11-30"),  # 구매일 > 기한 (D-003)
    ],
)
def test_db_rejects_bad_values(pg, two_users, over):
    a, _ = two_users
    with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.NumericValueOutOfRange)):
        create_food(pg, a["id"], **food_args(**over))


def test_purchase_date_may_equal_expiry_and_be_in_future(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args(purchase_date="2030-01-01", expiry_date="2030-01-01"))
    assert food["purchase_date"] == food["expiry_date"] == "2030-01-01"


def test_db_rejects_status_and_processed_date_mismatch(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    pg.commit()  # rollback 해도 식품이 남도록
    with pytest.raises(psycopg.errors.CheckViolation):  # none 인데 처리한 날짜가 있다
        pg.execute("UPDATE foods SET processed_date = '2026-11-02' WHERE id = %s", (food["id"],))
    pg.rollback()
    with pytest.raises(psycopg.errors.CheckViolation):  # eaten 인데 처리한 날짜가 없다
        pg.execute("UPDATE foods SET status = 'eaten' WHERE id = %s", (food["id"],))


def test_failed_write_changes_nothing(pg, two_users):
    a, _ = two_users
    food = create_food(pg, a["id"], **food_args())
    pg.commit()
    with pytest.raises(psycopg.errors.CheckViolation):
        update_food(pg, a["id"], food["id"], name="대파", quantity=0)
    pg.rollback()
    assert get_food(pg, a["id"], food["id"])["name"] == "양파"


def test_deleting_account_deletes_its_foods(pg, two_users):
    a, b = two_users
    create_food(pg, a["id"], **food_args())
    keep = create_food(pg, b["id"], **food_args())
    pg.execute("DELETE FROM users WHERE id = %s", (a["id"],))
    assert pg.execute("SELECT count(*) AS n FROM foods WHERE user_id = %s", (a["id"],)).fetchone()["n"] == 0
    assert get_food(pg, b["id"], keep["id"]) is not None


def test_unknown_account_cannot_own_food(pg):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        create_food(pg, str(uuid.uuid4()), **food_args())


def test_created_user_helper_is_independent(pg):
    # 같은 이메일이 아니면 계정은 얼마든지 만들 수 있고, 식품은 계정마다 따로다
    x = create_user(pg, "x@example.com", "Passw0rd!")
    y = create_user(pg, "y@example.com", "Passw0rd!")
    create_food(pg, x["id"], **food_args())
    assert list_active_foods(pg, y["id"]) == []
