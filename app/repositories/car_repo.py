"""Data-access layer for the Car resource.

Single-table CRUD helpers used directly by the ``cars`` endpoints. These
functions own their own transactions (``db.commit()``) because the
operations are not part of a multi-step business workflow — unlike rentals,
which require a service-layer transaction boundary.
"""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.car import Car, CarStatus
from app.models.rental import Rental
from app.schemas.car import CarCreate, CarUpdate


def create(db: Session, data: CarCreate) -> Car:
    """Insert a new car and commit the transaction.

    Args:
        db: The active SQLAlchemy database session.
        data: A ``CarCreate`` schema with the new car's fields.

    Returns:
        The newly persisted ``Car`` ORM instance, refreshed so server-set
        fields (``id``, ``created_at``, ``updated_at``) are populated.
    """
    car = Car(model=data.model, year=data.year, status=data.status)
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


def get(db: Session, car_id: int) -> Car | None:
    """Fetch a single car by primary key.

    Args:
        db: The active SQLAlchemy database session.
        car_id: Primary key of the car to retrieve.

    Returns:
        The ``Car`` ORM instance if found, otherwise ``None``.
    """
    return db.get(Car, car_id)


def list_cars(
    db: Session,
    status: CarStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Car]:
    """List cars with optional status filter and pagination.

    Results are ordered by ``id`` ascending so pagination is stable.

    Args:
        db: The active SQLAlchemy database session.
        status: Optional ``CarStatus`` to filter by. ``None`` returns all.
        limit: Maximum number of rows to return. Defaults to 50.
        offset: Number of rows to skip from the start of the result set.

    Returns:
        A list of ``Car`` ORM instances matching the filter.
    """
    stmt = select(Car).order_by(Car.id)
    if status is not None:
        stmt = stmt.where(Car.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def update(db: Session, car: Car, data: CarUpdate) -> Car:
    """Apply a partial update to an existing car and commit.

    Only fields explicitly set in ``data`` are written
    (``model_dump(exclude_unset=True)``) — unset fields are left untouched.

    Args:
        db: The active SQLAlchemy database session.
        car: The existing ``Car`` ORM instance to mutate.
        data: A ``CarUpdate`` schema with the fields to change.

    Returns:
        The updated ``Car`` ORM instance, refreshed from the database so
        ``updated_at`` reflects the new server timestamp.
    """
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(car, field, value)
    db.commit()
    db.refresh(car)
    return car


def delete(db: Session, car: Car) -> None:
    """Delete a car row and commit.

    Cascades to the car's rental history via ``ondelete="CASCADE"`` on the
    ``rentals.car_id`` foreign key. The endpoint guards against deleting
    cars with an active rental — see ``has_active_rental``.

    Args:
        db: The active SQLAlchemy database session.
        car: The ``Car`` ORM instance to delete.
    """
    db.delete(car)
    db.commit()


def has_active_rental(db: Session, car_id: int) -> bool:
    """Check whether a car has any rental whose ``end_time`` is ``NULL``.

    Used by the delete endpoint to prevent orphaning an in-progress rental.

    Args:
        db: The active SQLAlchemy database session.
        car_id: Primary key of the car to check.

    Returns:
        ``True`` if the car currently has at least one active rental,
        ``False`` otherwise.
    """
    stmt = select(exists().where(Rental.car_id == car_id, Rental.end_time.is_(None)))
    return bool(db.scalar(stmt))
