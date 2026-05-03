"""HTTP endpoints for the User resource.

CRUD over ``/api/v1/users``. All handlers are thin wrappers around
``user_repo`` with metric instrumentation via ``@track_operation``.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.metrics import track_operation
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@track_operation("user.create")
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """Create a new user.

    Args:
        payload: Validated request body containing the user's name.
        db: Injected database session (FastAPI dependency).

    Returns:
        The newly created user as a ``UserResponse`` DTO. HTTP 201.
    """
    user = user_repo.create(db, payload)
    logger.info("user.created id=%s name=%s", user.id, user.name)
    return UserResponse.model_validate(user)


@router.get("/", response_model=list[UserResponse])
@track_operation("user.list")
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    """List users with pagination, ordered by id ascending.

    Args:
        limit: Maximum number of rows to return (1–200, default 50).
        offset: Number of rows to skip (>= 0, default 0).
        db: Injected database session (FastAPI dependency).

    Returns:
        A list of ``UserResponse`` DTOs.
    """
    return [
        UserResponse.model_validate(u) for u in user_repo.list_users(db, limit, offset)
    ]


@router.get("/{user_id}", response_model=UserResponse)
@track_operation("user.get")
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    """Fetch a single user by id.

    Args:
        user_id: Path parameter identifying the user.
        db: Injected database session (FastAPI dependency).

    Returns:
        The user as a ``UserResponse`` DTO.

    Raises:
        HTTPException: 404 if no user exists with the given ``user_id``.
    """
    user = user_repo.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@track_operation("user.delete")
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a user.

    Refuses if the user has any active rental (``end_time`` is ``NULL``)
    to prevent orphaning an in-progress rental record.

    Args:
        user_id: Path parameter identifying the user to delete.
        db: Injected database session (FastAPI dependency).

    Returns:
        An empty 204 response on successful deletion.

    Raises:
        HTTPException: 404 if no user exists with the given ``user_id``.
        HTTPException: 409 if the user has at least one active rental.
    """
    user = user_repo.get(db, user_id)
    if user is None:
        logger.warning("user.delete.not_found id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user_repo.has_active_rental(db, user_id):
        logger.warning("user.delete.has_active_rental id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {user_id} has an active rental",
        )
    user_repo.delete(db, user)
    logger.info("user.deleted id=%s", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
