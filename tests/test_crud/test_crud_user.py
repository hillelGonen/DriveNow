"""Direct unit tests for app.crud.crud_user."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud import crud_car, crud_rental, crud_user
from app.models.user import User
from app.schemas.car import CarCreate
from app.schemas.rental import RentalCreate
from app.schemas.user import UserCreate


def test_create_persists_user(db_session: Session) -> None:
    user = crud_user.create(db_session, UserCreate(name="Ada"))
    assert user.id is not None
    assert user.name == "Ada"


def test_list_returns_inserted_users(db_session: Session) -> None:
    crud_user.create(db_session, UserCreate(name="A"))
    crud_user.create(db_session, UserCreate(name="B"))
    users = crud_user.list_users(db_session)
    assert {u.name for u in users} == {"A", "B"}


def test_has_active_rental_reflects_rental_state(
    db_session: Session, seed_user: User
) -> None:
    car = crud_car.create(db_session, CarCreate(model="X", year=2024))

    assert crud_user.has_active_rental(db_session, seed_user.id) is False

    rental = crud_rental.start_rental(
        db_session, RentalCreate(user_id=seed_user.id, car_id=car.id)
    )
    assert crud_user.has_active_rental(db_session, seed_user.id) is True

    crud_rental.return_car(db_session, rental.id)
    assert crud_user.has_active_rental(db_session, seed_user.id) is False


def test_delete_removes_user(db_session: Session) -> None:
    user = crud_user.create(db_session, UserCreate(name="Disposable"))
    user_id = user.id
    crud_user.delete(db_session, user)
    assert crud_user.get(db_session, user_id) is None
