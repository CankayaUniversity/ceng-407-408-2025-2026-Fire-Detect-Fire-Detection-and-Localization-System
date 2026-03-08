from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Flame Scope API"
    debug: bool = False

    # Database (SQLite varsayılan; PostgreSQL için .env ile override)
    database_url: str = "sqlite+aiosqlite:///./flamescope.db"
    # Sync URL for Alembic (SQLite: sqlite:///./flamescope.db)
    database_url_sync: str = "sqlite:///./flamescope.db"

    # JWT
    secret_key: str = "change-me-in-production-use-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Detector webhook (optional API key for POST /incidents/detected)
    detector_api_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
