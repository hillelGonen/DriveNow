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
