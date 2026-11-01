"""진짜 파일 DB 로 한 번 돌려 보는 시험.

다른 시험은 메모리 DB 를 쓴다. 여기서는 임시 폴더에 DB 파일 두 개를 만들고,
서버가 쓰는 연결 경로(환경 변수로 위치 지정, 요청마다 새 연결, 저장 확정)를 그대로 지난다.
임시 폴더는 시험이 끝나면 사라지고, 다른 분이 만드는 실제 DB 에는 닿지 않는다.
"""

import sqlite3

import pytest
from conftest import FOODS_SCHEMA, RULES_SCHEMA, TODAY, add_rule
from fastapi.testclient import TestClient

from app.database import get_today
from app.main import app


@pytest.fixture
def files(tmp_path, monkeypatch):
    foods_path = tmp_path / "fridge.db"
    rules_path = tmp_path / "rules.db"

    foods = sqlite3.connect(foods_path)
    foods.execute(FOODS_SCHEMA)
    foods.commit()
    foods.close()

    rules = sqlite3.connect(rules_path)
    for statement in RULES_SCHEMA:
        rules.execute(statement)
    add_rule(
        rules,
        "두부",
        "fridge",
        {"room": (False, None), "fridge": (True, 10), "freezer": (True, 30)},
    )
    rules.close()

    monkeypatch.setenv("FRIDGE_DB_PATH", str(foods_path))
    monkeypatch.setenv("RULES_DB_PATH", str(rules_path))
    app.dependency_overrides[get_today] = lambda: TODAY  # 오늘 날짜만 고정한다
    yield foods_path, rules_path
    app.dependency_overrides.clear()


BODY = {
    "name": "두부",
    "quantity": 2,
    "unit": "모",
    "purchase_date": "2026-10-30",
    "storage": "fridge",
}


def rows_in_file(path):
    connection = sqlite3.connect(path)
    try:
        return connection.execute("SELECT name, storage, status FROM foods").fetchall()
    finally:
        connection.close()


def test_whole_flow_works_with_real_files_and_is_really_saved(files):
    foods_path, _ = files
    client = TestClient(app)

    created = client.post("/foods", json=BODY)
    assert created.status_code == 201
    food_id = created.json()["id"]
    assert rows_in_file(foods_path) == [("두부", "fridge", "none")]  # 파일에 저장됐다

    assert [f["id"] for f in client.get("/foods").json()["foods"]] == [food_id]

    changed = client.patch(f"/foods/{food_id}/storage", json={"storage": "freezer"})
    assert changed.status_code == 200
    assert rows_in_file(foods_path) == [("두부", "freezer", "none")]

    processed = client.patch(f"/foods/{food_id}/process", json={"status": "eaten"})
    assert processed.status_code == 200
    assert rows_in_file(foods_path) == [("두부", "freezer", "eaten")]  # 행은 남는다
    assert client.get("/foods").json()["foods"] == []

    gone = client.delete(f"/foods/{food_id}")
    assert gone.status_code == 404  # 처리된 식품은 없는 식품과 같다 (D-037)


def test_delete_really_removes_the_row_from_the_file(files):
    foods_path, _ = files
    client = TestClient(app)
    food_id = client.post("/foods", json=BODY).json()["id"]
    assert client.delete(f"/foods/{food_id}").status_code == 204
    assert rows_in_file(foods_path) == []


def test_failed_request_leaves_the_file_unchanged(files):
    foods_path, _ = files
    client = TestClient(app)
    client.post("/foods", json=BODY)
    bad = client.post("/foods", json={**BODY, "quantity": 0})
    assert bad.status_code == 422
    assert rows_in_file(foods_path) == [("두부", "fridge", "none")]  # 한 건 그대로


def test_rules_file_is_opened_read_only(files):
    from app.database import _connect

    _, rules_path = files
    connection = _connect(rules_path, "ro")
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM rules")
    finally:
        connection.close()


def test_missing_db_file_is_a_500_and_no_file_is_created(tmp_path, monkeypatch):
    missing = tmp_path / "nope.db"
    monkeypatch.setenv("FRIDGE_DB_PATH", str(missing))
    client = TestClient(app)
    response = client.get("/foods")
    assert response.status_code == 500
    assert response.json()["reason"] == "load_failed"
    assert not missing.exists()  # 없는 파일을 새로 만들지 않는다


def test_db_without_the_tables_is_a_500_with_the_same_error_shape(tmp_path, monkeypatch):
    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()  # 표가 하나도 없는 DB
    monkeypatch.setenv("FRIDGE_DB_PATH", str(empty))
    client = TestClient(app)
    response = client.get("/foods")
    assert response.status_code == 500
    assert set(response.json()) == {"field", "reason", "message"}


def test_api_reads_the_db_made_by_init_db(tmp_path, monkeypatch):
    """init_db 가 만든 진짜 DB 를 API 가 그대로 읽는다 (파일 이름·환경 변수가 어긋나면 500)."""
    from app.db.init_db import init_db

    monkeypatch.setenv("FRIDGE_DB_PATH", str(tmp_path / "fridge.db"))
    monkeypatch.setenv("RULES_DB_PATH", str(tmp_path / "rules.db"))
    init_db()
    app.dependency_overrides[get_today] = lambda: TODAY
    try:
        client = TestClient(app)
        assert client.get("/foods").status_code == 200
        assert client.get("/rules", params={"q": "양파"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
