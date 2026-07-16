"""Application settings — loaded from environment / .env file."""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    branch_id: str = "00000000-0000-0000-0000-000000000001"
    branch_name: str = "Bai xe mac dinh"
    local_database_url: str = "sqlite+aiosqlite:///./data/parking_local.db"
    central_sync_enabled: bool = False
    central_database_url: str | None = None
    central_db_pool_recycle: int = 1800
    central_db_connect_timeout: int = 5
    sync_interval_seconds: int = 10
    sync_max_retry: int = 10
    sync_backoff_base_seconds: int = 5
    secret_key: str = "development-only-change-before-production-7e0430d4"
    access_token_expire_minutes: int = 480
    yolo_model_path: str | None = None
    ocr_engine: str = "vietocr"
    anpr_confidence_threshold: float = 0.75


@lru_cache
def get_settings() -> Settings:
    return Settings()
