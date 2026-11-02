"""계정 표 읽기·쓰기와 비밀번호 해시 (US-012).

- 이메일은 앞뒤 공백을 지우고 소문자로 바꿔 저장하고 찾는다 (Q-02, Q-06).
- 비밀번호는 원문으로 저장하지 않는다. argon2 해시 문자열 하나에 사용자마다 다른 솔트가 들어 있다 (D-094, Q-11).
- 이메일 모양(D-096)·비밀번호 규칙(D-047)·로그인 실패 문구는 API 가 판단한다. 여기서는 저장만 한다.
- commit 은 하지 않는다. 부르는 쪽이 한 묶음으로 처리한다.
"""
import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


class EmailTaken(Exception):
    """이미 가입된 이메일 (email_taken 409). 동시에 두 번 가입해 UNIQUE 에 걸린 경우도 같다."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_user(conn: psycopg.Connection, email: str, password: str) -> dict:
    """계정을 만든다. 이미 있는 이메일이면 EmailTaken. 돌려주는 값은 {"id", "email"} (해시는 내보내지 않는다)."""
    email = normalize_email(email)
    try:
        # 실패한 문장이 바깥 묶음 전체를 망가뜨리지 않게 savepoint 안에서 한다
        with conn.transaction():
            row = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
                (email, hash_password(password)),
            ).fetchone()
    except psycopg.errors.UniqueViolation as error:
        raise EmailTaken(email) from error
    return {"id": str(row["id"]), "email": row["email"]}


def find_user_by_email(conn: psycopg.Connection, email: str) -> dict | None:
    """로그인용. {"id", "email", "password_hash"} 또는 None."""
    row = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email = %s", (normalize_email(email),)
    ).fetchone()
    if row is None:
        return None
    return {"id": str(row["id"]), "email": row["email"], "password_hash": row["password_hash"]}


def authenticate(conn: psycopg.Connection, email: str, password: str) -> dict | None:
    """이메일·비밀번호가 맞으면 {"id", "email"}, 아니면 None.

    그 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다 (V-17, D-057).
    """
    user = find_user_by_email(conn, email)
    if user is None:
        verify_password(_DUMMY_HASH, password)  # 없는 이메일도 걸리는 시간이 비슷하도록
        return None
    if not verify_password(user["password_hash"], password):
        return None
    return {"id": user["id"], "email": user["email"]}


_DUMMY_HASH = hash_password("dummy-password-for-timing")
