"""Pydantic schemas for the User resource."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Request body for creating a new user.

    Attributes:
        name: Full name of the user (1–200 chars).
    """

    name: str = Field(..., min_length=1, max_length=200)


class UserResponse(BaseModel):
    """Response schema for user endpoints.

    Built from a ``User`` ORM instance via ``UserResponse.model_validate(u)``.

    Attributes:
        id: Database primary key.
        name: Full name of the user.
        created_at: UTC timestamp when the user was created.
        updated_at: UTC timestamp of the most recent modification.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
