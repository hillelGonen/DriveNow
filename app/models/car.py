"""ORM model and status enum for the Car entity."""

import enum

from sqlalchemy import Column, Enum as SQLEnum, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class CarStatus(str, enum.Enum):
    """Lifecycle states of a car in the fleet.

    Inherits from ``str`` so values serialise cleanly to JSON and can be
    compared directly with string literals.

    Attributes:
        AVAILABLE: Car is ready to be rented. Default state for new cars.
        IN_USE: Car is part of an active rental. Cannot be booked again
            until the current rental is returned.
        MAINTENANCE: Car is temporarily out of service. Not available for
            new rentals.
    """

    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"


class Car(Base, TimestampMixin):
    """ORM model representing a vehicle in the DriveNow fleet.

    Maps to the ``cars`` table. The ``status`` column is indexed to support
    efficient filtering by availability. The ``rentals`` relationship uses
    ``cascade="all, delete-orphan"`` so deleting a car also removes its
    rental history — guarded at the API layer by an active-rental check.

    Attributes:
        id: Auto-incremented primary key.
        model: Make and model string (e.g. ``"Tesla Model Y"``), max 100 chars.
        year: Manufacturing year, constrained to 1900–2100 at the schema layer.
        status: Current availability state; defaults to ``AVAILABLE`` on insert.
        rentals: Back-populated list of associated ``Rental`` ORM instances.
    """

    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(CarStatus, name="carstatus"),
        nullable=False,
        default=CarStatus.AVAILABLE,
        index=True,
    )

    rentals = relationship(
        "Rental",
        back_populates="car",
        cascade="all, delete-orphan",
    )
