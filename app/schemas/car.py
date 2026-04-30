from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.car import CarStatus


class CarBase(BaseModel):
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2100)


class CarCreate(CarBase):
    status: CarStatus = CarStatus.AVAILABLE


class CarUpdate(BaseModel):
    """Partial update. Any subset of fields may be provided."""

    model: str | None = Field(default=None, min_length=1, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
    status: CarStatus | None = None


class CarRead(CarBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CarStatus
    created_at: datetime
    updated_at: datetime
