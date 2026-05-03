"""HTTP endpoints for the Rental resource.

Endpoints under ``/api/v1/rentals`` delegate the full transactional
workflow to ``RentalService``. The handlers' only responsibilities are
to invoke the service, translate domain exceptions into HTTP responses,
and serialise the result through ``RentalResponse``.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.metrics import track_operation
from app.repositories.rental_repo import (
    CarNotAvailableError,
    RentalAlreadyReturnedError,
    RentalNotFoundError,
)
from app.schemas.rental import RentalCreate, RentalResponse
from app.services.rental_service import RentalService

router = APIRouter(prefix="/rentals", tags=["rentals"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=RentalResponse, status_code=status.HTTP_201_CREATED)
@track_operation("rental.start")
def start_rental(
    payload: RentalCreate, db: Session = Depends(get_db)
) -> RentalResponse:
    """Start a new rental for the given user and car.

    Delegates the full start workflow (lock car → validate AVAILABLE →
    insert rental → flip car to IN_USE → commit → publish event) to
    ``RentalService``. Concurrent booking attempts on the same car
    serialise at the database via ``SELECT FOR UPDATE``.

    Args:
        payload: Validated request body with ``user_id`` and ``car_id``.
        db: Injected database session (FastAPI dependency).

    Returns:
        The newly created rental as a ``RentalResponse`` DTO. HTTP 201.

    Raises:
        HTTPException: 400 if the car does not exist or its status is
            not ``AVAILABLE``.
    """
    try:
        rental = RentalService(db).start_rental(payload)
    except CarNotAvailableError as exc:
        logger.warning("rental.start.rejected car_id=%s reason=%s", payload.car_id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    logger.info(
        "rental.started id=%s user_id=%s car_id=%s",
        rental.id,
        rental.user_id,
        rental.car_id,
    )
    return RentalResponse.model_validate(rental)


@router.patch("/{rental_id}/return", response_model=RentalResponse)
@track_operation("rental.return")
def return_rental(rental_id: int, db: Session = Depends(get_db)) -> RentalResponse:
    """Mark a rental as returned and free the associated car.

    Delegates to ``RentalService.return_rental``: stamps ``end_time``,
    flips the car back to ``AVAILABLE``, commits, and publishes the
    ``rental.ended`` event. A second return on the same rental is
    rejected idempotently with HTTP 400.

    Args:
        rental_id: Path parameter identifying the rental to return.
        db: Injected database session (FastAPI dependency).

    Returns:
        The updated rental as a ``RentalResponse`` DTO.

    Raises:
        HTTPException: 404 if no rental exists with the given ``rental_id``.
        HTTPException: 400 if the rental was already returned previously.
    """
    try:
        rental = RentalService(db).return_rental(rental_id)
    except RentalNotFoundError as exc:
        logger.warning("rental.return.not_found id=%s", rental_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except RentalAlreadyReturnedError as exc:
        logger.warning("rental.return.already_returned id=%s", rental_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    logger.info(
        "rental.returned id=%s car_id=%s end_time=%s",
        rental.id,
        rental.car_id,
        rental.end_time.isoformat(),
    )
    return RentalResponse.model_validate(rental)
