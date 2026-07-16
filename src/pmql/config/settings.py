"""Application settings — loaded from environment / .env file.

Keys here MUST match `.env.example` at the repo root.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Branch identity
    branch_id: str = "00000000-0000-0000-0000-000000000001"
    branch_name: str = "Bai xe mac dinh"

    # Local database (always required — this app is local-first)
    local_database_url: str = "sqlite+aiosqlite:///./data/parking_local.db"

    # Central sync (optional — app must run fully offline without it)
    central_sync_enabled: bool = False
    central_database_url: str | None = None
    central_db_pool_recycle: int = 1800
    central_db_connect_timeout: int = 5

    sync_interval_seconds: int = 10
    sync_max_retry: int = 10
    sync_backoff_base_seconds: int = 5

    # Auth
    secret_key: str = "CHANGE_ME_RANDOM_64_CHARS"
    access_token_expire_minutes: int = 480

    # ANPR / hardware (optional at runtime — mock adapters used if absent)
    yolo_model_path: str | None = None
    ocr_engine: str = "vietocr"
    anpr_confidence_threshold: float = 0.75


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
