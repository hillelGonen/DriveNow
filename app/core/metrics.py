import inspect
import time
from functools import wraps

from prometheus_client import Counter, Histogram

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
    """Decorator for service methods. Records duration + outcome.

    Works on both sync and async callables — detects coroutine functions
    so service-layer code can use one decorator regardless of style.
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
