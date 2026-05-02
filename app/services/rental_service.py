"""Rental service layer.

Owns the transaction boundary, business rules (status validation,
idempotency), and event emission for rentals. Delegates pure data
access to app.repositories.rental_repo.
"""

import logging

from sqlalchemy.orm import Session

from app.events.publisher import publish
from app.models.car import CarStatus
from app.models.rental import Rental
from app.repositories import rental_repo
from app.repositories.rental_repo import (
    CarNotAvailableError,
    RentalAlreadyReturnedError,
    RentalNotFoundError,
)
from app.schemas.rental import RentalCreate

logger = logging.getLogger(__name__)


class RentalService:
    """Business logic for the rental lifecycle.

    Sequence (start): lock car -> validate AVAILABLE -> insert rental ->
    flip car to IN_USE -> commit -> publish event.

    Sequence (return): load rental -> guard already-returned -> lock car
    -> stamp end_time -> flip car to AVAILABLE -> commit -> publish event.

    The car-row SELECT FOR UPDATE serializes concurrent bookings of the
    same car at the database level, so the AVAILABLE check is race-free.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def start_rental(self, data: RentalCreate) -> Rental:
        car = rental_repo.lock_car(self.db, data.car_id)
        if car is None:
            raise CarNotAvailableError(f"Car {data.car_id} does not exist")
        if car.status != CarStatus.AVAILABLE:
            raise CarNotAvailableError(
                f"Car {car.id} is not available (status={car.status.value})"
            )

        rental = rental_repo.insert_rental(self.db, data)
        car.status = CarStatus.IN_USE

        self.db.commit()
        self.db.refresh(rental)

        publish(
            "rental.started",
            {
                "rental_id": rental.id,
                "car_id": car.id,
                "user_id": rental.user_id,
                "start_time": rental.start_time.isoformat(),
            },
        )
        return rental

    def return_rental(self, rental_id: int) -> Rental:
        rental = rental_repo.get(self.db, rental_id)
        if rental is None:
            raise RentalNotFoundError(f"Rental {rental_id} not found")
        if rental.end_time is not None:
            raise RentalAlreadyReturnedError(
                f"Rental {rental_id} was already returned at "
                f"{rental.end_time.isoformat()}"
            )

        car = rental_repo.lock_car(self.db, rental.car_id)
        rental_repo.stamp_end_time(rental)
        if car is not None:
            car.status = CarStatus.AVAILABLE

        self.db.commit()
        self.db.refresh(rental)

        publish(
            "rental.ended",
            {
                "rental_id": rental.id,
                "car_id": rental.car_id,
                "user_id": rental.user_id,
                "end_time": rental.end_time.isoformat(),
            },
        )
        return rental
