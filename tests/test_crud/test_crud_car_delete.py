"""Direct unit tests for car delete + has_active_rental guard."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud import crud_car, crud_rental
from app.models.user import User
from app.schemas.car import CarCreate
from app.schemas.rental import RentalCreate


def test_has_active_rental_false_for_unrented_car(db_session: Session) -> None:
    car = crud_car.create(db_session, CarCreate(model="X", year=2024))
    assert crud_car.has_active_rental(db_session, car.id) is False


def test_has_active_rental_true_during_rental(
    db_session: Session, seed_user: User
) -> None:
    car = crud_car.create(db_session, CarCreate(model="X", year=2024))
    rental = crud_rental.start_rental(
        db_session, RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    assert crud_car.has_active_rental(db_session, car.id) is True

    crud_rental.return_car(db_session, rental.id)
    assert crud_car.has_active_rental(db_session, car.id) is False


def test_delete_removes_car(db_session: Session) -> None:
    car = crud_car.create(db_session, CarCreate(model="Disposable", year=2024))
    car_id = car.id
    crud_car.delete(db_session, car)
    assert crud_car.get(db_session, car_id) is None
