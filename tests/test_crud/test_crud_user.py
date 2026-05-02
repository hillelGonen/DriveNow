"""Direct unit tests for app.repositories.user_repo."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories import car_repo, user_repo
from app.models.user import User
from app.schemas.car import CarCreate
from app.schemas.rental import RentalCreate
from app.schemas.user import UserCreate
from app.services.rental_service import RentalService


def test_create_persists_user(db_session: Session) -> None:
    user = user_repo.create(db_session, UserCreate(name="Ada"))
    assert user.id is not None
    assert user.name == "Ada"


def test_list_returns_inserted_users(db_session: Session) -> None:
    user_repo.create(db_session, UserCreate(name="A"))
    user_repo.create(db_session, UserCreate(name="B"))
    users = user_repo.list_users(db_session)
    assert {u.name for u in users} == {"A", "B"}


def test_has_active_rental_reflects_rental_state(
    db_session: Session, seed_user: User
) -> None:
    car = car_repo.create(db_session, CarCreate(model="X", year=2024))

    assert user_repo.has_active_rental(db_session, seed_user.id) is False

    service = RentalService(db_session)
    rental = service.start_rental(
        RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    assert user_repo.has_active_rental(db_session, seed_user.id) is True

    service.return_rental(rental.id)
    assert user_repo.has_active_rental(db_session, seed_user.id) is False


def test_delete_removes_user(db_session: Session) -> None:
    user = user_repo.create(db_session, UserCreate(name="Disposable"))
    user_id = user.id
    user_repo.delete(db_session, user)
    assert user_repo.get(db_session, user_id) is None
