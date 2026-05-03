"""Pydantic schemas for the Car resource.

These DTOs are the only types that cross the HTTP boundary. ORM ``Car``
instances are converted via ``CarRead.model_validate(car)`` before being
serialised to the client; incoming requests are validated against
``CarCreate`` or ``CarUpdate`` before reaching the repository layer.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.car import CarStatus


class CarBase(BaseModel):
    """Shared fields for car create and read operations.

    Attributes:
        model: Make and model of the car (1–100 chars).
        year: Manufacturing year, constrained to 1900–2100.
    """

    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2100)


class CarCreate(CarBase):
    """Request body for creating a new car.

    Attributes:
        status: Initial lifecycle status. Defaults to ``AVAILABLE``.
    """

    status: CarStatus = CarStatus.AVAILABLE


class CarUpdate(BaseModel):
    """Request body for partial car updates (PATCH).

    All fields are optional. Only fields explicitly provided by the client
    are updated on the target row — ``model_dump(exclude_unset=True)`` is
    used by the repository to build the update payload.

    Attributes:
        model: New make/model string, if changing.
        year: New manufacturing year, if changing.
        status: New lifecycle status, if changing.
    """

    model: str | None = Field(default=None, min_length=1, max_length=100)
    year: int | None = Field(default=None, ge=1900, le=2100)
    status: CarStatus | None = None


class CarRead(CarBase):
    """Response schema for car endpoints.

    Built from a ``Car`` ORM instance via ``CarRead.model_validate(car)``.
    The ``from_attributes=True`` config enables direct attribute lookup
    on the ORM object.

    Attributes:
        id: Database primary key.
        status: Current lifecycle status.
        created_at: UTC timestamp when the car was created.
        updated_at: UTC timestamp of the most recent modification.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CarStatus
    created_at: datetime
    updated_at: datetime
