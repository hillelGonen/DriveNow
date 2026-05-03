"""Pydantic schemas for the Rental resource."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RentalCreate(BaseModel):
    """Request body for starting a new rental.

    Attributes:
        user_id: Primary key of the renting user. Must reference an
            existing ``User`` row.
        car_id: Primary key of the car to rent. Must reference an
            existing ``Car`` row whose status is ``AVAILABLE``.
    """

    user_id: int
    car_id: int


class RentalResponse(BaseModel):
    """Response schema for rental endpoints.

    Built from a ``Rental`` ORM instance via ``RentalResponse.model_validate(r)``.

    Attributes:
        id: Database primary key.
        user_id: Foreign key referencing the renting user.
        car_id: Foreign key referencing the rented car.
        start_time: UTC timestamp when the rental began.
        end_time: UTC timestamp when the rental was returned, or ``None``
            if the rental is still active.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    car_id: int
    start_time: datetime
    end_time: datetime | None
