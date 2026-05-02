"""Smoke test for car CRUD endpoints.

Uses an in-memory SQLite database so the test is fast and self-contained
(no Docker / Postgres required). The production stack still uses Postgres
via Alembic; this test exercises the API + repositories + ORM contract only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client() -> TestClient:
    # StaticPool + a single shared connection: all sessions see the same
    # in-memory SQLite DB. Without it, sessionmaker hands out fresh
    # connections, each with its own (empty) in-memory database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_create_and_list_car(client: TestClient) -> None:
    payload = {"model": "Tesla Model Y", "year": 2024}
    create_resp = client.post("/api/v1/cars", json=payload)
    assert create_resp.status_code == 201, create_resp.text

    body = create_resp.json()
    assert body["model"] == "Tesla Model Y"
    assert body["year"] == 2024
    assert body["status"] == "AVAILABLE"
    assert isinstance(body["id"], int)

    list_resp = client.get("/api/v1/cars")
    assert list_resp.status_code == 200
    cars = list_resp.json()
    assert len(cars) == 1
    assert cars[0]["id"] == body["id"]

    filtered = client.get("/api/v1/cars", params={"status": "MAINTENANCE"})
    assert filtered.status_code == 200
    assert filtered.json() == []
