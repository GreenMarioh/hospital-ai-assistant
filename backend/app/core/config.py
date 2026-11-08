from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "dev"
    secret_key: str = "dev-insecure-secret-key-change-me-please"
    field_encryption_key: str = ""
    cors_origins: str = "http://localhost:3000"
    hospital_timezone: str = "Asia/Kolkata"

    database_url: str = "postgresql+asyncpg://hospital_app:change-me-too@db:5432/hospital"
    migration_database_url: str = ""

    gemini_api_key: str = ""
    # Free-tier-safe defaults (see docs/DECISIONS.md); use a stronger GEMINI_MODEL on a paid key.
    gemini_model: str = "gemini-3.5-flash-lite"  # clinical: triage, summaries
    gemini_flash_model: str = "gemini-3.1-flash-lite"  # conversational: booking assistant, FAQ
    # optional: minimal|low|medium|high; empty omits the parameter (model default)
    gemini_thinking_level: str = ""
    gemini_flash_thinking_level: str = ""
    ai_enabled: bool = True

    storage_backend: str = "local"
    upload_dir: str = "/data/uploads"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    email_backend: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    sentry_dsn: str = ""
    redis_url: str = ""  # shared rate-limit counters across workers; empty = per-process memory
    clamav_host: str = ""
    clamav_port: int = 3310
    clamav_timeout: float = 10.0
    audit_log_stream_path: str = (
        ""  # optional: append-only JSONL stream for tamper-evident external storage
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
