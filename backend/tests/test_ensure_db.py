"""서버가 켜질 때 DB 파일이 없으면 만들고, 있으면 건드리지 않는지 본다.

임시 폴더만 쓴다. 실제 backend/data 에는 닿지 않는다.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.db.init_db import ensure_db
from app.main import app


@pytest.fixture
def paths(tmp_path, monkeypatch):
    foods_path = tmp_path / "data" / "fridge.db"  # data 폴더도 없는 상태에서 시작한다
    rules_path = tmp_path / "data" / "rules.db"
    monkeypatch.setenv("FRIDGE_DB_PATH", str(foods_path))
    monkeypatch.setenv("RULES_DB_PATH", str(rules_path))
    return foods_path, rules_path


def count(path, table):
    connection = sqlite3.connect(path)
    try:
        return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        connection.close()


def test_creates_both_files_and_fills_rules_when_missing(paths):
    foods_path, rules_path = paths
    ensure_db()
    assert foods_path.exists() and rules_path.exists()
    assert count(foods_path, "foods") == 0
    assert count(rules_path, "rules") == 30


def test_keeps_existing_files_untouched(paths):
    foods_path, rules_path = paths
    ensure_db()

    foods = sqlite3.connect(foods_path)
    foods.execute(
        "INSERT INTO foods (id, name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " VALUES (?, '두부', 'fridge', 1, '모', '2026-10-30', '2026-11-05', 'manual')",
        ("a" * 36,),
    )
    foods.commit()
    foods.close()
    rules = sqlite3.connect(rules_path)
    rules.execute("DELETE FROM rules WHERE name = '양파'")  # 개발자가 규칙표를 고친 상황
    rules.commit()
    rules.close()

    ensure_db()
    assert count(foods_path, "foods") == 1
    assert count(rules_path, "rules") == 29  # 다시 채워지지 않는다


def test_creates_only_the_missing_file(paths):
    foods_path, rules_path = paths
    ensure_db()
    rules_path.unlink()
    foods = sqlite3.connect(foods_path)
    foods.execute(
        "INSERT INTO foods (id, name, storage, quantity, unit, purchase_date, expiry_date, source)"
        " VALUES (?, '두부', 'fridge', 1, '모', '2026-10-30', '2026-11-05', 'manual')",
        ("b" * 36,),
    )
    foods.commit()
    foods.close()

    ensure_db()
    assert count(rules_path, "rules") == 30
    assert count(foods_path, "foods") == 1


def test_server_start_creates_db_so_home_loads(paths):
    foods_path, _ = paths
    with TestClient(app) as client:  # with 로 열어야 서버 시작 단계가 실행된다
        response = client.get("/foods")
    assert foods_path.exists()
    assert response.status_code == 200
    assert response.json()["foods"] == []
