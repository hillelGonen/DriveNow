"""Data-access layer for the User resource.

Single-table CRUD helpers used directly by the ``users`` endpoints.
These functions own their own transactions because user operations are
not part of a multi-step business workflow.
"""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.rental import Rental
from app.models.user import User
from app.schemas.user import UserCreate


def create(db: Session, data: UserCreate) -> User:
    """Insert a new user and commit the transaction.

    Args:
        db: The active SQLAlchemy database session.
        data: A ``UserCreate`` schema with the new user's fields.

    Returns:
        The newly persisted ``User`` ORM instance, refreshed so server-set
        fields (``id``, ``created_at``, ``updated_at``) are populated.
    """
    user = User(name=data.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get(db: Session, user_id: int) -> User | None:
    """Fetch a single user by primary key.

    Args:
        db: The active SQLAlchemy database session.
        user_id: Primary key of the user to retrieve.

    Returns:
        The ``User`` ORM instance if found, otherwise ``None``.
    """
    return db.get(User, user_id)


def list_users(db: Session, limit: int = 50, offset: int = 0) -> list[User]:
    """List users with pagination, ordered by id ascending.

    Args:
        db: The active SQLAlchemy database session.
        limit: Maximum number of rows to return. Defaults to 50.
        offset: Number of rows to skip from the start of the result set.

    Returns:
        A list of ``User`` ORM instances.
    """
    stmt = select(User).order_by(User.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def delete(db: Session, user: User) -> None:
    """Delete a user row and commit.

    Cascades to the user's rental history via ``ondelete="CASCADE"`` on the
    ``rentals.user_id`` foreign key. The endpoint guards against deleting
    users with an active rental — see ``has_active_rental``.

    Args:
        db: The active SQLAlchemy database session.
        user: The ``User`` ORM instance to delete.
    """
    db.delete(user)
    db.commit()


def has_active_rental(db: Session, user_id: int) -> bool:
    """Check whether a user has any rental whose ``end_time`` is ``NULL``.

    Used by the delete endpoint to prevent orphaning an in-progress rental.

    Args:
        db: The active SQLAlchemy database session.
        user_id: Primary key of the user to check.

    Returns:
        ``True`` if the user currently has at least one active rental,
        ``False`` otherwise.
    """
    stmt = select(exists().where(Rental.user_id == user_id, Rental.end_time.is_(None)))
    return bool(db.scalar(stmt))
