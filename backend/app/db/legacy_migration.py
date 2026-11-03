"""기존 식품(v0.2.0)을 처음 가입한 사람에게 넘기기 (D-042 ~ D-045, D-097, DATA-MODEL 7절).

옛 SQLite 식품을 가져오는 일은 서버가 하지 않는다. 알렘빅 버전 파일이 단계적으로 한다.
  0002 옛 식품을 foods 로 가져오기(주인 없이) → 0003 이전용 계정 만들기 → 0004 주인 없는 식품을 이전용 계정에 넘기기
  → 0005 주인 칸을 비울 수 없게 바꾸기 → 0007 첫 계정과 옮김 여부를 적는 표(legacy_migration) 만들기
이전용 계정은 로그인할 수 없는 계정이라, 여기서 마지막 단계를 한다: 첫 계정이 생기면 이전용 계정이
맡고 있던 식품을 그 계정으로 넘긴다. 이후 가입하는 계정은 넘겨받을 것이 없어서 빈 상태로 시작한다 (D-044).

묶음은 둘로 나뉜다 (DATA-MODEL 7-3). commit 은 이 파일에서 하지 않는다.
  ① 가입 묶음: 계정·로그인 상태와 함께 register_first_account 로 첫 계정을 적는다. 실패하면 가입이 취소된다.
  ② 넘기기 묶음: claim_if_first_account. 실패하면 이 묶음만 취소된다. 계정은 그대로이고(D-097), 첫 계정이
     다음에 로그인할 때 성공할 때까지 다시 시도한다. 줄을 잠그므로 두 기기에서 동시에 해도 한 번만 넘어간다.
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


def register_first_account(conn: psycopg.Connection, user_id: str) -> bool:
    """이 계정이 첫 계정이면 옮김 기록(legacy_migration)에 적고 True. 이미 첫 계정이 있으면 False.

    두 사람이 동시에 처음 가입해도 줄은 한 개뿐이라(id = 1) 한 사람만 True 를 받는다.
    """
    cur = conn.execute(
        "INSERT INTO legacy_migration (id, user_id) VALUES (1, %s) ON CONFLICT (id) DO NOTHING",
        (user_id,),
    )
    return cur.rowcount == 1


def claim_if_first_account(conn: psycopg.Connection, user_id: str) -> int:
    """첫 계정이고 아직 못 넘겨받았으면 식품을 넘기고 옮김 끝으로 적는다. 넘긴 식품 수를 돌려준다(아니면 0).

    넘기기와 "옮김 끝" 표시는 같은 묶음이다. 실패하면 둘 다 취소돼 일부만 넘어간 채 남지 않는다 (D-097).
    """
    row = conn.execute(
        "SELECT 1 FROM legacy_migration WHERE id = 1 AND user_id = %s AND NOT migrated FOR UPDATE",
        (user_id,),
    ).fetchone()
    if row is None:
        return 0
    moved = claim_legacy_foods(conn, user_id)
    conn.execute("UPDATE legacy_migration SET migrated = true WHERE id = 1")
    return moved
