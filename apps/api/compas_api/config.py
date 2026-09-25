"""Settings (env-driven, with sane local defaults)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMPAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local SQLite DB. Lives next to the api dir.
    db_path: str = "compas.db"

    # Local storage dir for original audio + stems
    storage_dir: str = "storage"

    # CORS — allow the SvelteKit dev server
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
    ]

    # ML — if true, ML jobs run inline in the API; if false, push to worker queue
    run_ml_inline: bool = True

    # Max upload size
    max_upload_mb: int = 100


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure storage dir exists
        Path(_settings.storage_dir).mkdir(parents=True, exist_ok=True)
    return _settings
