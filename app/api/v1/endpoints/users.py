import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.metrics import track_operation
from app.crud import crud_user
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@track_operation("user.create")
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    user = crud_user.create(db, payload)
    logger.info("user.created id=%s name=%s", user.id, user.name)
    return UserResponse.model_validate(user)


@router.get("/", response_model=list[UserResponse])
@track_operation("user.list")
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    return [
        UserResponse.model_validate(u) for u in crud_user.list_users(db, limit, offset)
    ]


@router.get("/{user_id}", response_model=UserResponse)
@track_operation("user.get")
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    user = crud_user.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@track_operation("user.delete")
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    user = crud_user.get(db, user_id)
    if user is None:
        logger.warning("user.delete.not_found id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if crud_user.has_active_rental(db, user_id):
        logger.warning("user.delete.has_active_rental id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {user_id} has an active rental",
        )
    crud_user.delete(db, user)
    logger.info("user.deleted id=%s", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
