import enum

from sqlalchemy import Column, Enum as SQLEnum, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class CarStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"


class Car(Base, TimestampMixin):
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
