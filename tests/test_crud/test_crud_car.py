"""Direct unit tests for app.repositories.car_repo.

Hits the repository layer with a real Session (in-memory SQLite via the
shared `db_session` fixture in tests/conftest.py). Bypasses FastAPI
entirely so we exercise the data-access contract on its own.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import car_repo
from app.models.car import CarStatus
from app.schemas.car import CarCreate, CarUpdate


def test_create_persists_with_default_status(db_session: Session) -> None:
    car = car_repo.create(db_session, CarCreate(model="Tesla Model Y", year=2024))
    assert car.id is not None
    assert car.status == CarStatus.AVAILABLE
    assert car.model == "Tesla Model Y"


def test_list_filters_by_status(db_session: Session) -> None:
    car_repo.create(db_session, CarCreate(model="A", year=2020))
    car_repo.create(
        db_session, CarCreate(model="B", year=2021, status=CarStatus.MAINTENANCE)
    )
    car_repo.create(
        db_session, CarCreate(model="C", year=2022, status=CarStatus.MAINTENANCE)
    )

    available = car_repo.list_cars(db_session, status=CarStatus.AVAILABLE)
    maintenance = car_repo.list_cars(db_session, status=CarStatus.MAINTENANCE)
    everything = car_repo.list_cars(db_session)

    assert {c.model for c in available} == {"A"}
    assert {c.model for c in maintenance} == {"B", "C"}
    assert len(everything) == 3


def test_update_partial_only_touches_provided_fields(db_session: Session) -> None:
    car = car_repo.create(db_session, CarCreate(model="Original", year=2020))
    updated = car_repo.update(db_session, car, CarUpdate(status=CarStatus.IN_USE))
    assert updated.status == CarStatus.IN_USE
    assert updated.model == "Original"
    assert updated.year == 2020
