"""Application entry point for DriveNow.

Configures the FastAPI application: registers Prometheus instrumentation,
mounts fleet-gauge collectors, includes API routers, and manages startup
and shutdown lifecycle logging.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import REGISTRY

from app.api.v1.endpoints import cars as cars_router
from app.api.v1.endpoints import rentals as rentals_router
from app.api.v1.endpoints import users as users_router
from app.core import metrics as _metrics  # noqa: F401 -- register service instruments
from app.core.metrics import FleetCollector
from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle.

    Logs a startup message when the application begins accepting requests
    and a shutdown message when it stops. FastAPI invokes this context
    manager automatically; it replaces the deprecated ``@app.on_event`` hooks.

    Args:
        app: The FastAPI application instance injected by the framework.

    Yields:
        Control to FastAPI while the application is running.
    """
    logger.info("application.startup name=%s", settings.APP_NAME)
    yield
    logger.info("application.shutdown name=%s", settings.APP_NAME)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

try:
    REGISTRY.register(FleetCollector())
    logger.info("metrics.collector_registered")
except ValueError:
    logger.debug("metrics.collector_already_registered")

app.include_router(cars_router.router, prefix="/api/v1")
app.include_router(rentals_router.router, prefix="/api/v1")
app.include_router(users_router.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe endpoint.

    Returns a static response to indicate the process is alive. Used by
    load balancers and container orchestrators. Does not verify database
    or Redis connectivity.

    Returns:
        A dict with a single ``status`` key set to ``"ok"``.
    """
    return {"status": "ok"}
