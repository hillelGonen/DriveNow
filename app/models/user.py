"""ORM model for the User entity."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """ORM model representing a registered DriveNow customer.

    Maps to the ``users`` table. The ``rentals`` relationship uses
    ``cascade="all, delete-orphan"`` so deleting a user also removes
    their rental history — guarded at the API layer by an active-rental check.

    Attributes:
        id: Auto-incremented primary key.
        name: Full name of the user, max 200 chars, required.
        rentals: Back-populated list of associated ``Rental`` ORM instances.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)

    rentals = relationship(
        "Rental", back_populates="user", cascade="all, delete-orphan"
    )
