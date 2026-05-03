"""ORM model for the Rental entity."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Rental(Base, TimestampMixin):
    """ORM model representing a single car rental transaction.

    Maps to the ``rentals`` table. A rental is considered *active* when
    ``end_time`` is ``NULL``; it is *completed* once ``end_time`` is set.
    Both foreign keys use ``ON DELETE CASCADE`` so rental rows are removed
    automatically if the referenced car or user is deleted — the API layer
    guards against deletion of entities with active rentals.

    Attributes:
        id: Auto-incremented primary key.
        user_id: Foreign key referencing the renting ``User``. Indexed for
            efficient per-user rental lookups.
        car_id: Foreign key referencing the rented ``Car``. Indexed for
            efficient per-car rental lookups and the active-rental guard.
        start_time: UTC timestamp set by the database when the row is inserted.
        end_time: UTC timestamp stamped by the service when the car is returned.
            ``NULL`` indicates an active rental.
        car: Back-populated ``Car`` ORM instance.
        user: Back-populated ``User`` ORM instance.
    """

    __tablename__ = "rentals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    car_id = Column(
        Integer,
        ForeignKey("cars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    end_time = Column(DateTime(timezone=True), nullable=True)

    car = relationship("Car", back_populates="rentals")
    user = relationship("User", back_populates="rentals")
