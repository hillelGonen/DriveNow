"""Thin data-access layer for rentals.

Repository layer: focused strictly on database operations. No business
logic, no transaction management (caller commits), no event publishing.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.car import Car
from app.models.rental import Rental
from app.schemas.rental import RentalCreate


class CarNotAvailableError(Exception):
    """Raised when a rental cannot start because the car is not AVAILABLE."""


class RentalNotFoundError(Exception):
    """Raised when a rental id does not exist."""


class RentalAlreadyReturnedError(Exception):
    """Raised when return_car is called on a rental whose end_time is set."""


def lock_car(db: Session, car_id: int) -> Car | None:
    """SELECT ... FOR UPDATE on the car row. Caller commits."""
    return db.query(Car).filter(Car.id == car_id).with_for_update().one_or_none()


def insert_rental(db: Session, data: RentalCreate) -> Rental:
    """Insert a rental row and flush so .id is populated. Caller commits."""
    rental = Rental(user_id=data.user_id, car_id=data.car_id)
    db.add(rental)
    db.flush()
    return rental


def get(db: Session, rental_id: int) -> Rental | None:
    return db.get(Rental, rental_id)


def stamp_end_time(rental: Rental) -> None:
    """Set rental.end_time to UTC now. Pure mutation, caller commits."""
    rental.end_time = datetime.now(timezone.utc)
