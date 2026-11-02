"""기존 식품(v0.2.0)을 처음 가입한 사람에게 넘기기 (D-042 ~ D-045, DATA-MODEL 7절).

옛 SQLite 식품을 가져오는 일은 서버가 하지 않는다. 알렘빅 버전 파일이 단계적으로 한다.
  0002 옛 식품을 foods 로 가져오기(주인 없이) → 0003 이전용 계정 만들기 → 0004 주인 없는 식품을 이전용 계정에 넘기기
  → 0005 주인 칸을 비울 수 없게 바꾸기
이전용 계정은 로그인할 수 없는 계정이라, 여기서 마지막 단계를 한다: 처음 가입하는 계정이 생기면 이전용 계정이
맡고 있던 식품을 그 계정으로 넘긴다. 이후 가입하는 계정은 넘겨받을 것이 없어서 빈 상태로 시작한다 (D-044).

- 가입 묶음(transaction) 안에서 부른다. 두 사람이 동시에 처음 가입해도 식품은 한 사람에게만 간다
  (먼저 넘긴 쪽이 행을 잠그고, 나중 쪽은 이미 주인이 바뀐 행을 찾지 못한다).
- 가입과 같은 묶음이라 넘기기가 실패하면 가입도 취소된다. 다시 가입하면 된다.
- commit 은 하지 않는다.
"""
import psycopg

# 알렘빅 0003·0004 의 이전용 계정 이메일과 같은 값이다 (시험이 같은지 확인한다).
LEGACY_EMAIL = "legacy@fridge.invalid"


def claim_legacy_foods(conn: psycopg.Connection, user_id: str) -> int:
    """이전용 계정이 맡고 있던 식품을 이 계정으로 넘긴다. 넘긴 식품 수를 돌려준다."""
    cur = conn.execute(
        "UPDATE foods SET user_id = %s WHERE user_id = (SELECT id FROM users WHERE email = %s)",
        (user_id, LEGACY_EMAIL),
    )
    return cur.rowcount
