"""Direct unit tests for app.crud.crud_rental.

Covers the business invariants that live in the CRUD layer today:
- start_rental flips car to IN_USE
- start_rental rejects an already-busy car
- return_car is idempotent (second call raises)
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.crud import crud_car, crud_rental
from app.crud.crud_rental import CarNotAvailableError, RentalAlreadyReturnedError
from app.models.car import CarStatus
from app.models.user import User
from app.schemas.car import CarCreate
from app.schemas.rental import RentalCreate


@pytest.fixture()
def car(db_session: Session):
    return crud_car.create(db_session, CarCreate(model="Tesla Model Y", year=2024))


def test_start_rental_flips_car_to_in_use(
    db_session: Session, seed_user: User, car
) -> None:
    rental = crud_rental.start_rental(
        db_session, RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    db_session.refresh(car)

    assert rental.id is not None
    assert rental.end_time is None
    assert car.status == CarStatus.IN_USE


def test_start_rental_rejects_unavailable_car(
    db_session: Session, seed_user: User, car
) -> None:
    crud_rental.start_rental(
        db_session, RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    with pytest.raises(CarNotAvailableError, match="not available"):
        crud_rental.start_rental(
            db_session, RentalCreate(user_id=seed_user.id, car_id=car.id)
        )


def test_return_car_is_idempotent(db_session: Session, seed_user: User, car) -> None:
    rental = crud_rental.start_rental(
        db_session, RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    crud_rental.return_car(db_session, rental.id)
    with pytest.raises(RentalAlreadyReturnedError):
        crud_rental.return_car(db_session, rental.id)
