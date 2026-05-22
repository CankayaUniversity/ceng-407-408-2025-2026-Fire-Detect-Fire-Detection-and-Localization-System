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
    refresh_token_expire_days: int = 7

    # Detector webhook (optional API key for POST /incidents/detected)
    detector_api_key: str | None = None

    # Supabase Storage for incident snapshots
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "incident-snapshots"
    snapshot_upload_max_mb: int = 5
    supabase_upload_timeout_seconds: int = 15

    # Incident decision policy
    critical_risk_threshold: float = 0.97
    auto_escalation_risk_threshold: float = 0.80
    auto_escalation_seconds: int = 30

    # Firebase Admin SDK
    firebase_credentials_path: str = "firebase-adminsdk.json"
    firebase_credentials_json_base64: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
