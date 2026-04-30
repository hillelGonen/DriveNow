from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)

    rentals = relationship("Rental", back_populates="user", cascade="all, delete-orphan")
