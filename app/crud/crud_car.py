from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.car import Car, CarStatus
from app.schemas.car import CarCreate, CarUpdate


def create(db: Session, data: CarCreate) -> Car:
    car = Car(model=data.model, year=data.year, status=data.status)
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


def get(db: Session, car_id: int) -> Car | None:
    return db.get(Car, car_id)


def list_cars(
    db: Session,
    status: CarStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Car]:
    stmt = select(Car).order_by(Car.id)
    if status is not None:
        stmt = stmt.where(Car.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def update(db: Session, car: Car, data: CarUpdate) -> Car:
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(car, field, value)
    db.commit()
    db.refresh(car)
    return car
