from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Rental(Base, TimestampMixin):
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
