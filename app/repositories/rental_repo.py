"""Thin data-access layer for rentals.

Repository layer: focused strictly on database operations. No business
logic, no transaction management (caller commits), no event publishing.

Domain exceptions live in ``app.services.exceptions`` — not here — so
that the endpoint layer depends only on the service contract.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.car import Car
from app.models.rental import Rental
from app.schemas.rental import RentalCreate


def lock_car(db: Session, car_id: int) -> Car | None:
    """Acquire a row-level lock on a car record.

    Issues a ``SELECT ... FOR UPDATE`` query, which blocks any other
    transaction attempting to lock the same row. This serializes concurrent
    rental start and return operations on the same car, making status checks
    race-free. The caller is responsible for committing or rolling back the
    enclosing transaction to release the lock.

    Args:
        db: The active SQLAlchemy database session.
        car_id: The primary key of the car to lock.

    Returns:
        The locked ``Car`` ORM instance, or ``None`` if no car with the
        given ``car_id`` exists.
    """
    return db.query(Car).filter(Car.id == car_id).with_for_update().one_or_none()


def lock_rental(db: Session, rental_id: int) -> Rental | None:
    """Acquire a row-level lock on a rental record.

    Issues a ``SELECT ... FOR UPDATE`` query on the rental row, preventing
    concurrent return requests from both passing the ``end_time is None``
    guard and double-stamping the return time. The caller is responsible
    for committing or rolling back the enclosing transaction to release
    the lock.

    Args:
        db: The active SQLAlchemy database session.
        rental_id: The primary key of the rental to lock.

    Returns:
        The locked ``Rental`` ORM instance, or ``None`` if no rental with
        the given ``rental_id`` exists.
    """
    return db.query(Rental).filter(Rental.id == rental_id).with_for_update().one_or_none()


def insert_rental(db: Session, data: RentalCreate) -> Rental:
    """Insert a new rental record and flush it to the database.

    Adds the rental to the session and calls ``db.flush()`` so the database
    assigns a primary key (``rental.id``). The record is not yet committed —
    the caller must call ``db.commit()`` to persist the change.

    Args:
        db: The active SQLAlchemy database session.
        data: A ``RentalCreate`` schema containing the ``user_id`` and
            ``car_id`` for the new rental.

    Returns:
        The newly flushed ``Rental`` ORM instance with ``id`` populated
        by the database.
    """
    rental = Rental(user_id=data.user_id, car_id=data.car_id)
    db.add(rental)
    db.flush()
    return rental


def get(db: Session, rental_id: int) -> Rental | None:
    """Fetch a single rental by primary key without locking.

    Use ``lock_rental`` instead when the caller needs to guard a
    concurrent write (e.g. ``return_rental``).

    Args:
        db: The active SQLAlchemy database session.
        rental_id: The primary key of the rental to retrieve.

    Returns:
        The ``Rental`` ORM instance if found, or ``None`` if no rental
        with the given ``rental_id`` exists.
    """
    return db.get(Rental, rental_id)


def stamp_end_time(rental: Rental) -> None:
    """Set the rental's end_time to the current UTC timestamp.

    Pure in-memory mutation — no database I/O is performed. The caller
    must call ``db.commit()`` to persist the change.

    Args:
        rental: The ``Rental`` ORM instance to update. Modified in place.
    """
    rental.end_time = datetime.now(timezone.utc)
