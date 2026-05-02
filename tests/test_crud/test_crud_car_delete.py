"""Direct unit tests for car delete + has_active_rental guard."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import car_repo
from app.models.user import User
from app.schemas.car import CarCreate
from app.schemas.rental import RentalCreate
from app.services.rental_service import RentalService


def test_has_active_rental_false_for_unrented_car(db_session: Session) -> None:
    car = car_repo.create(db_session, CarCreate(model="X", year=2024))
    assert car_repo.has_active_rental(db_session, car.id) is False


def test_has_active_rental_true_during_rental(
    db_session: Session, seed_user: User
) -> None:
    car = car_repo.create(db_session, CarCreate(model="X", year=2024))
    service = RentalService(db_session)
    rental = service.start_rental(
        RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    assert car_repo.has_active_rental(db_session, car.id) is True

    service.return_rental(rental.id)
    assert car_repo.has_active_rental(db_session, car.id) is False


def test_delete_removes_car(db_session: Session) -> None:
    car = car_repo.create(db_session, CarCreate(model="Disposable", year=2024))
    car_id = car.id
    car_repo.delete(db_session, car)
    assert car_repo.get(db_session, car_id) is None
