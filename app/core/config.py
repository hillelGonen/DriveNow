"""Application settings loaded from environment variables and the .env file.

Uses pydantic-settings so every field can be overridden by an environment
variable of the same name. The settings instance is process-scoped and
cached via ``@lru_cache`` so the file and environment are read only once.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration for the DriveNow application.

    Field values are resolved in this order (highest priority first):
    environment variables → ``.env`` file → field defaults.

    Attributes:
        APP_NAME: Human-readable application name used in logs and the
            OpenAPI title.
        DATABASE_URL: SQLAlchemy-compatible connection string for the
            PostgreSQL database.
        LOG_LEVEL: Minimum log level for the root logger
            (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``).
        LOG_FILE: Absolute path to the rotating log file written by the
            application. The directory is created automatically if absent.
        REDIS_URL: Connection URL for the Redis instance used by the event
            publisher. Must be reachable from the application container.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "DriveNow"
    DATABASE_URL: str = "postgresql+psycopg2://drivenow:drivenow@db:5432/drivenow"
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/app/logs/app.log"
    REDIS_URL: str = "redis://redis:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Reads environment variables and the ``.env`` file on first call, then
    returns the same ``Settings`` instance on every subsequent call within
    the process lifetime.

    Returns:
        The process-scoped ``Settings`` instance.
    """
    return Settings()
