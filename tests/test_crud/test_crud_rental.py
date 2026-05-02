"""Direct unit tests for the rental flow.

After the Phase 4.5 refactor, business invariants live on
RentalService (app.services.rental_service). The repository layer
(app.repositories.rental_repo) is pure data access and is not
exercised here on its own.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.car import CarStatus
from app.models.user import User
from app.repositories import car_repo
from app.repositories.rental_repo import (
    CarNotAvailableError,
    RentalAlreadyReturnedError,
)
from app.schemas.car import CarCreate
from app.schemas.rental import RentalCreate
from app.services.rental_service import RentalService


@pytest.fixture()
def car(db_session: Session):
    return car_repo.create(db_session, CarCreate(model="Tesla Model Y", year=2024))


def test_start_rental_flips_car_to_in_use(
    db_session: Session, seed_user: User, car
) -> None:
    rental = RentalService(db_session).start_rental(
        RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    db_session.refresh(car)

    assert rental.id is not None
    assert rental.end_time is None
    assert car.status == CarStatus.IN_USE


def test_start_rental_rejects_unavailable_car(
    db_session: Session, seed_user: User, car
) -> None:
    service = RentalService(db_session)
    service.start_rental(RentalCreate(user_id=seed_user.id, car_id=car.id))
    with pytest.raises(CarNotAvailableError, match="not available"):
        service.start_rental(RentalCreate(user_id=seed_user.id, car_id=car.id))


def test_return_car_is_idempotent(
    db_session: Session, seed_user: User, car
) -> None:
    service = RentalService(db_session)
    rental = service.start_rental(RentalCreate(user_id=seed_user.id, car_id=car.id))
    service.return_rental(rental.id)
    with pytest.raises(RentalAlreadyReturnedError):
        service.return_rental(rental.id)
