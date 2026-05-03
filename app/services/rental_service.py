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

    Orchestrates the full start and return flows, enforcing business rules,
    managing the transaction boundary, and publishing domain events post-commit.

    The car-row SELECT FOR UPDATE serializes concurrent bookings of the same
    car at the database level, making the AVAILABLE status check race-free.

    Sequence (start):
        lock car → validate AVAILABLE → insert rental →
        flip car to IN_USE → commit → publish ``rental.started``.

    Sequence (return):
        load rental → guard already-returned → lock car →
        stamp end_time → flip car to AVAILABLE → commit → publish ``rental.ended``.

    Attributes:
        db: The active SQLAlchemy database session. This service is the sole
            owner of ``db.commit()`` for all rental operations.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the service with a database session.

        Args:
            db: An active SQLAlchemy ``Session`` injected via FastAPI's
                dependency system. The service owns the transaction boundary
                for all operations it performs.
        """
        self.db = db

    def start_rental(self, data: RentalCreate) -> Rental:
        """Start a new rental for a given user and car.

        Acquires a row-level lock on the car to prevent double-booking under
        concurrent requests. Validates that the car exists and is in the
        ``AVAILABLE`` status before inserting the rental record and flipping
        the car to ``IN_USE``. Commits the transaction and publishes a
        ``rental.started`` domain event post-commit so consumers only ever
        observe committed state.

        Args:
            data: A ``RentalCreate`` schema containing the ``user_id`` and
                ``car_id`` for the new rental.

        Returns:
            The newly created and committed ``Rental`` ORM instance, refreshed
            from the database so all server-set fields (e.g. ``start_time``,
            ``id``) are populated.

        Raises:
            CarNotAvailableError: If the car identified by ``data.car_id``
                does not exist, or its status is not ``AVAILABLE``
                (e.g. ``IN_USE`` or ``MAINTENANCE``).
        """
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
        """Process the return of an active rental.

        Loads the rental and enforces idempotency — a rental whose
        ``end_time`` is already set is rejected immediately. Then acquires a
        row-level lock on the associated car, stamps the ``end_time`` with the
        current UTC time, and flips the car back to ``AVAILABLE``. Commits the
        transaction and publishes a ``rental.ended`` domain event post-commit.

        Args:
            rental_id: The primary key of the ``Rental`` record to return.

        Returns:
            The updated and committed ``Rental`` ORM instance, refreshed from
            the database so ``end_time`` and any other server-set fields
            reflect their final persisted values.

        Raises:
            RentalNotFoundError: If no rental with the given ``rental_id``
                exists in the database.
            RentalAlreadyReturnedError: If the rental's ``end_time`` is
                already set, indicating it was previously returned. Prevents
                silent mutation of ``end_time`` on repeated calls.
        """
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
