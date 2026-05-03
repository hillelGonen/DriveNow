"""SQLAlchemy declarative base and shared mixins for all ORM models."""

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all DriveNow ORM models.

    All models that inherit from ``Base`` are tracked by SQLAlchemy's
    metadata and included in Alembic's autogenerate migrations.
    """


class TimestampMixin:
    """Mixin that adds ``created_at`` and ``updated_at`` timestamp columns.

    All timestamps are stored as UTC-aware ``timestamptz`` in PostgreSQL.
    Application code must construct datetimes with ``datetime.now(timezone.utc)``
    — naive datetimes must never be persisted. A rental system spans timezones
    and "server local time" assumptions cause silent off-by-hours bugs at
    booking boundaries.

    Attributes:
        created_at: UTC timestamp set by the database when the row is inserted.
        updated_at: UTC timestamp updated by the database on every row modification.
    """

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
