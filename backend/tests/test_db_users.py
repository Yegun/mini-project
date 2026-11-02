"""계정 저장소 (PostgreSQL). 이메일 정리, 중복 가입, 비밀번호 해시를 본다."""
import psycopg
import pytest

from app.db.users_repo import (
    EmailTaken,
    authenticate,
    create_user,
    find_user_by_email,
    hash_password,
    normalize_email,
    verify_password,
)


def test_email_is_trimmed_and_lowercased(pg):
    user = create_user(pg, "  Kim@Example.COM ", "Passw0rd!")
    assert user["email"] == "kim@example.com"
    assert find_user_by_email(pg, "KIM@example.com")["id"] == user["id"]


def test_same_email_in_other_case_is_taken(pg):
    create_user(pg, "kim@example.com", "Passw0rd!")
    with pytest.raises(EmailTaken):
        create_user(pg, "KIM@example.com ", "Other1234!")


def test_duplicate_does_not_break_outer_transaction(pg):
    """가입 묶음 안에서 중복이 걸려도 같은 묶음의 다른 일은 계속할 수 있다."""
    create_user(pg, "kim@example.com", "Passw0rd!")
    pg.commit()
    with pytest.raises(EmailTaken):
        create_user(pg, "kim@example.com", "Passw0rd!")
    assert pg.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1


def test_db_rejects_uppercase_email(pg):
    with pytest.raises(psycopg.errors.CheckViolation):
        pg.execute("INSERT INTO users (email, password_hash) VALUES ('Kim@example.com', 'x')")


def test_password_is_not_stored_in_plain_text(pg):
    create_user(pg, "kim@example.com", "Passw0rd!")
    stored = find_user_by_email(pg, "kim@example.com")["password_hash"]
    assert "Passw0rd!" not in stored
    assert stored.startswith("$argon2")


def test_each_user_has_different_salt(pg):
    a = create_user(pg, "a@example.com", "Same1234!")
    b = create_user(pg, "b@example.com", "Same1234!")
    hash_a = find_user_by_email(pg, a["email"])["password_hash"]
    hash_b = find_user_by_email(pg, b["email"])["password_hash"]
    assert hash_a != hash_b


def test_authenticate_success_and_failures(pg):
    user = create_user(pg, "kim@example.com", "Passw0rd!")
    assert authenticate(pg, "KIM@example.com", "Passw0rd!") == user
    assert authenticate(pg, "kim@example.com", "wrong") is None
    assert authenticate(pg, "nobody@example.com", "Passw0rd!") is None  # 어느 쪽이 틀렸는지 구분하지 않는다
    assert authenticate(pg, "", "") is None


def test_verify_handles_broken_hash():
    assert verify_password("not-a-hash", "x") is False
    assert verify_password(hash_password("abc"), "abc") is True


def test_normalize_email():
    assert normalize_email("  A@B.C ") == "a@b.c"


def test_create_user_does_not_commit_by_itself(pg):
    """한 요청의 첫 문장이어도 commit 하지 않는다. 부르는 쪽이 rollback 하면 계정이 남지 않는다."""
    create_user(pg, "kim@example.com", "Passw0rd!")
    pg.rollback()
    assert pg.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 0
