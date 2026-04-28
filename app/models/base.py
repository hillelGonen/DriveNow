from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """All timestamps are stored as UTC-aware (Postgres `timestamptz`).

    Application code must construct datetimes via `datetime.now(timezone.utc)`
    (or `datetime.now(UTC)` on Python 3.11+). Naive datetimes must never be
    persisted: a rental system spans timezones and "server time" assumptions
    cause silent off-by-hours bugs at booking boundaries.
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
