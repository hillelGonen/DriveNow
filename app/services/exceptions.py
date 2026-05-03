"""Domain exceptions for the rental service layer.

These exceptions represent business-rule violations, not data-layer errors.
They are raised by ``RentalService`` and caught by the endpoint layer,
which maps them to appropriate HTTP status codes.

Keeping exceptions here (service layer) rather than in the repository layer
ensures that endpoints depend only on the service contract — not on
repository internals.
"""


class CarNotAvailableError(Exception):
    """Raised when a rental cannot start because the car does not exist
    or its status is not ``AVAILABLE``."""


class RentalNotFoundError(Exception):
    """Raised when no rental exists for the given primary key."""


class RentalAlreadyReturnedError(Exception):
    """Raised when a return is attempted on a rental whose ``end_time``
    is already set."""
