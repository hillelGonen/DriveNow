"""Prometheus instrumentation for the DriveNow service layer.

Provides two complementary instrumentation mechanisms:

1. ``track_operation(name)`` — a decorator that records the duration and
   outcome (``success`` / ``error``) of any sync or async callable as
   labelled Histogram and Counter metrics.

2. ``FleetCollector`` — a custom Prometheus collector that queries the
   database at every ``/metrics`` scrape to expose live fleet gauges
   (``drivenow_available_cars``, ``drivenow_active_rentals``).
"""

import inspect
import time
from functools import wraps

from prometheus_client import Counter, Histogram

from prometheus_client.core import GaugeMetricFamily, REGISTRY

SERVICE_OPERATION_DURATION = Histogram(
    "drivenow_service_operation_duration_seconds",
    "Duration of service-layer business operations",
    labelnames=("operation", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

SERVICE_OPERATION_TOTAL = Counter(
    "drivenow_service_operation_total",
    "Count of service-layer operations",
    labelnames=("operation", "status"),
)


def track_operation(name: str):
    """Decorator that records duration and outcome of a service operation.

    Wraps the decorated callable in a try/finally block that observes
    elapsed time and increments ``drivenow_service_operation_duration_seconds``
    and ``drivenow_service_operation_total`` with labels ``operation=name``
    and ``status=success|error``. Exceptions are re-raised after recording.

    Works transparently on both sync and async callables — coroutine
    functions are detected via ``inspect.iscoroutinefunction`` so endpoints
    and services can use a single decorator style regardless of async/sync.

    Args:
        name: The operation label written to Prometheus (e.g. ``"car.create"``
            or ``"rental.start"``). Should be a stable dotted string — changing
            it breaks dashboards and alerts.

    Returns:
        A decorator that wraps the target callable with metrics recording.

    Example:
        .. code-block:: python

            @router.post("/cars")
            @track_operation("car.create")
            def create_car(payload: CarCreate, db: Session = Depends(get_db)):
                ...
    """

    def decorator(fn):
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                status = "success"
                start = time.perf_counter()
                try:
                    return await fn(*args, **kwargs)
                except Exception:
                    status = "error"
                    raise
                finally:
                    SERVICE_OPERATION_DURATION.labels(name, status).observe(
                        time.perf_counter() - start
                    )
                    SERVICE_OPERATION_TOTAL.labels(name, status).inc()

            return async_wrapper

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            status = "success"
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                SERVICE_OPERATION_DURATION.labels(name, status).observe(
                    time.perf_counter() - start
                )
                SERVICE_OPERATION_TOTAL.labels(name, status).inc()

        return sync_wrapper

    return decorator


class FleetCollector:
    """Custom Prometheus collector for live fleet and rental gauges.

    Registered with the global ``REGISTRY`` at application startup.
    Prometheus scrapes ``/metrics`` and calls ``collect()`` on every
    registered collector, so the gauge values always reflect the current
    database state at scrape time — no caching, no drift.

    Metrics exposed:
        drivenow_available_cars: Number of cars whose status is ``AVAILABLE``.
        drivenow_active_rentals: Number of rentals with no ``end_time``
            (i.e. currently ongoing).
    """

    def collect(self):
        """Query the database and yield current fleet gauge values.

        Opens a short-lived session for each scrape, queries the car and
        rental tables, then closes the session in a ``finally`` block.
        Imports are deferred inside the method to avoid circular imports
        at module load time.

        Yields:
            ``GaugeMetricFamily`` instances for ``drivenow_available_cars``
            and ``drivenow_active_rentals``.
        """
        # Deferred to avoid circular import: metrics ← database ← config
        from app.core.database import SessionLocal
        from app.models.car import Car, CarStatus
        from app.models.rental import Rental

        db = SessionLocal()
        try:
            available_count = (
                db.query(Car).filter(Car.status == CarStatus.AVAILABLE).count()
            )
            yield GaugeMetricFamily(
                "drivenow_available_cars",
                "Current count of cars with AVAILABLE status",
                value=available_count,
            )

            active_rentals = db.query(Rental).filter(Rental.end_time == None).count()
            yield GaugeMetricFamily(
                "drivenow_active_rentals",
                "Current count of ongoing rentals",
                value=active_rentals,
            )
        finally:
            db.close()
