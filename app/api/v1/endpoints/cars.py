import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.metrics import track_operation
from app.crud import crud_car
from app.models.car import CarStatus
from app.schemas.car import CarCreate, CarRead, CarUpdate

router = APIRouter(prefix="/cars", tags=["cars"])
logger = logging.getLogger(__name__)


@router.post("", response_model=CarRead, status_code=status.HTTP_201_CREATED)
@track_operation("car.create")
def create_car(payload: CarCreate, db: Session = Depends(get_db)) -> CarRead:
    car = crud_car.create(db, payload)
    logger.info("car.created id=%s model=%s year=%s", car.id, car.model, car.year)
    return CarRead.model_validate(car)


@router.get("", response_model=list[CarRead])
@track_operation("car.list")
def list_cars(
    status_filter: CarStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[CarRead]:
    cars = crud_car.list_cars(db, status=status_filter, limit=limit, offset=offset)
    return [CarRead.model_validate(c) for c in cars]


@router.patch("/{car_id}", response_model=CarRead)
@track_operation("car.update")
def update_car(car_id: int, payload: CarUpdate, db: Session = Depends(get_db)) -> CarRead:
    car = crud_car.get(db, car_id)
    if car is None:
        logger.warning("car.update.not_found id=%s", car_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")
    updated = crud_car.update(db, car, payload)
    logger.info(
        "car.updated id=%s changes=%s",
        updated.id,
        payload.model_dump(exclude_unset=True),
    )
    return CarRead.model_validate(updated)
