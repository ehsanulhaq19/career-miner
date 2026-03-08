from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/careerminer"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    MAX_SCRAP_EXECUTION_TIME_MINUTES: int = 30
    APP_NAME: str = "CareerMiner"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
