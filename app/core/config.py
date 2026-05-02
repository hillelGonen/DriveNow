from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    return Settings()
