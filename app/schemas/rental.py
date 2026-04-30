from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RentalCreate(BaseModel):
    user_id: int
    car_id: int


class RentalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    car_id: int
    start_time: datetime
    end_time: datetime | None
