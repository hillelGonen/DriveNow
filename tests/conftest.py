"""Shared fixtures for API tests.

Uses an in-memory SQLite DB so tests are fast and self-contained
(no Docker / Postgres required). The fixture suite mirrors the prod
session lifecycle: the API uses the overridden `get_db`, while the test
also gets a direct `db_session` to seed reference rows (e.g. a User the
rental test needs to exist before it POSTs).
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, User


@pytest.fixture()
def engine():
    """Fresh in-memory SQLite engine per test.

    StaticPool: every session shares one connection, so the tables created
    here are visible to every later session. Without it, sessionmaker
    hands out fresh connections, each with its own (empty) in-memory DB.
    """
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session(session_factory) -> Iterator[Session]:
    """Direct session for seeding test data outside the API."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def api_client(session_factory) -> Iterator[TestClient]:
    """TestClient with `get_db` overridden to use the in-memory engine."""

    def override_get_db():
        db = session_factory()
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


@pytest.fixture()
def seed_user(db_session: Session) -> User:
    """Insert a Test User and return it. Required by the rental test
    because there is no User CRUD endpoint."""
    user = User(name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
