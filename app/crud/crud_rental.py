from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.car import Car, CarStatus
from app.models.rental import Rental
from app.schemas.rental import RentalCreate


class CarNotAvailableError(Exception):
    """Raised when a rental cannot start because the car is not AVAILABLE."""


class RentalNotFoundError(Exception):
    """Raised when a rental id does not exist."""


class RentalAlreadyReturnedError(Exception):
    """Raised when return_car is called on a rental whose end_time is set."""


def start_rental(db: Session, data: RentalCreate) -> Rental:
    """Atomically start a rental.

    Locks the car row (SELECT ... FOR UPDATE) so concurrent bookings of
    the same car serialize at the DB. Without the lock, two requests
    could both pass the AVAILABLE check before either flips the status.
    """
    car = db.query(Car).filter(Car.id == data.car_id).with_for_update().one_or_none()
    if car is None:
        raise CarNotAvailableError(f"Car {data.car_id} does not exist")
    if car.status != CarStatus.AVAILABLE:
        raise CarNotAvailableError(
            f"Car {car.id} is not available (status={car.status.value})"
        )

    rental = Rental(user_id=data.user_id, car_id=data.car_id)
    car.status = CarStatus.IN_USE
    db.add(rental)
    db.commit()
    db.refresh(rental)
    return rental


def return_car(db: Session, rental_id: int) -> Rental:
    rental = db.get(Rental, rental_id)
    if rental is None:
        raise RentalNotFoundError(f"Rental {rental_id} not found")
    if rental.end_time is not None:
        raise RentalAlreadyReturnedError(
            f"Rental {rental_id} was already returned at {rental.end_time.isoformat()}"
        )

    car = db.query(Car).filter(Car.id == rental.car_id).with_for_update().one()

    # Explicit UTC-aware datetime to stay consistent with the column's
    # server_default=func.now() (which Postgres returns as timestamptz).
    rental.end_time = datetime.now(timezone.utc)
    car.status = CarStatus.AVAILABLE
    db.commit()
    db.refresh(rental)
    return rental
