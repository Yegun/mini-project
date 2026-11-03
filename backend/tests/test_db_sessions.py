"""로그인 상태 저장소 (PostgreSQL). 기기별 줄, 30분 만료, 해시 저장을 본다."""
from app.db.sessions_repo import check_session, create_session, delete_session


def age(conn, minutes):
    """모든 로그인 상태의 마지막 사용 시각을 minutes 분 전으로 돌린다 (시험용)."""
    conn.execute("UPDATE sessions SET last_used_at = now() - make_interval(mins => %s)", (minutes,))


def test_valid_session_returns_user(pg, two_users):
    a, _ = two_users
    token = create_session(pg, a["id"])
    assert check_session(pg, token) == a["id"]


def test_db_stores_only_hash_of_token(pg, two_users):
    a, _ = two_users
    token = create_session(pg, a["id"])
    stored = [r["id"] for r in pg.execute("SELECT id FROM sessions")]
    assert token not in stored and len(stored) == 1


def test_missing_or_unknown_token_is_rejected(pg, two_users):
    assert check_session(pg, None) is None
    assert check_session(pg, "") is None
    assert check_session(pg, "never-issued") is None


def test_request_within_30_minutes_refreshes_time(pg, two_users):
    a, _ = two_users
    token = create_session(pg, a["id"])
    age(pg, 29)
    assert check_session(pg, token) == a["id"]  # 29분: 아직 살아 있다
    recent = pg.execute(
        "SELECT last_used_at > clock_timestamp() - interval '1 minute' AS ok FROM sessions"
    ).fetchone()["ok"]
    assert recent  # 마지막 사용 시각이 방금으로 갱신됐다


def test_session_expires_after_30_minutes_and_is_not_revived(pg, two_users):
    a, _ = two_users
    token = create_session(pg, a["id"])
    age(pg, 31)
    assert check_session(pg, token) is None
    assert pg.execute("SELECT count(*) AS n FROM sessions").fetchone()["n"] == 0  # 거절하면서 줄을 지운다
    assert check_session(pg, token) is None  # 거절된 요청이 로그인 상태를 되살리지 않는다


def test_devices_are_independent(pg, two_users):
    a, _ = two_users
    phone = create_session(pg, a["id"])
    laptop = create_session(pg, a["id"])
    assert phone != laptop
    assert delete_session(pg, phone) is True
    assert check_session(pg, phone) is None
    assert check_session(pg, laptop) == a["id"]  # 한 기기의 로그아웃은 다른 기기에 영향이 없다 (D-054)
    assert delete_session(pg, phone) is False


def test_login_clears_only_own_expired_sessions(pg, two_users):
    a, b = two_users
    old_a = create_session(pg, a["id"])
    old_b = create_session(pg, b["id"])
    age(pg, 31)
    new_a = create_session(pg, a["id"])
    assert pg.execute("SELECT count(*) AS n FROM sessions WHERE user_id = %s", (a["id"],)).fetchone()["n"] == 1
    assert check_session(pg, new_a) == a["id"]
    assert check_session(pg, old_a) is None
    # 다른 계정의 만료된 줄은 그 계정이 거절될 때 지워진다 (여기서는 건드리지 않았다)
    assert pg.execute("SELECT count(*) AS n FROM sessions WHERE user_id = %s", (b["id"],)).fetchone()["n"] == 1
    assert check_session(pg, old_b) is None


def test_deleting_account_ends_its_sessions(pg, two_users):
    a, _ = two_users
    token = create_session(pg, a["id"])
    pg.execute("DELETE FROM users WHERE id = %s", (a["id"],))
    assert check_session(pg, token) is None
