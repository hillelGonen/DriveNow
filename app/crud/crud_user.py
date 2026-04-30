from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.rental import Rental
from app.models.user import User
from app.schemas.user import UserCreate


def create(db: Session, data: UserCreate) -> User:
    user = User(name=data.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def list_users(db: Session, limit: int = 50, offset: int = 0) -> list[User]:
    stmt = select(User).order_by(User.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def delete(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def has_active_rental(db: Session, user_id: int) -> bool:
    stmt = select(
        exists().where(Rental.user_id == user_id, Rental.end_time.is_(None))
    )
    return bool(db.scalar(stmt))
