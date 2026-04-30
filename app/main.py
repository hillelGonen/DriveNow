import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.endpoints import cars as cars_router
from app.api.v1.endpoints import rentals as rentals_router
from app.core import metrics as _metrics  # noqa: F401 -- register service instruments
from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application.startup name=%s", settings.APP_NAME)
    yield
    logger.info("application.shutdown name=%s", settings.APP_NAME)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(cars_router.router, prefix="/api/v1")
app.include_router(rentals_router.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
