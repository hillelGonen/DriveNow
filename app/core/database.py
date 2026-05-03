"""SQLAlchemy engine, session factory, and FastAPI database dependency.

The engine is created once at module import time using the configured
``DATABASE_URL``. ``get_db`` is the FastAPI dependency that yields one
session per request and guarantees the connection is returned to the pool
even if the handler raises.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a scoped database session.

    Opens a new ``Session`` from the shared connection pool, yields it to
    the route handler, then closes it in a ``finally`` block so the
    underlying connection is always returned to the pool — even when the
    handler raises an exception.

    Yields:
        An active ``Session`` bound to the configured PostgreSQL database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
