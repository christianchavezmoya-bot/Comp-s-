"""Settings (env-driven, with sane local defaults)."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """Walk up from this file to find the project root (contains 'apps' and 'packages')."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "apps").is_dir() and (parent / "packages").is_dir():
            return parent
    return here.parent.parent  # fallback


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMPAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Local SQLite DB. Lives at <project>/storage/compas.db by default.
    db_path: str = ""

    # Local storage dir for original audio + stems
    storage_dir: str = ""

    # CORS — allow the SvelteKit dev server
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
    ]

    # ML — if true, ML jobs run inline in the API; if false, push to worker queue
    run_ml_inline: bool = True

    # Use the higher-quality htdemucs_ft model (slower). Default: fast htdemucs.
    use_htdemucs_ft: bool = False

    # Transcribe lyrics (Whisper). Adds significant time.
    transcribe: bool = False

    # Word-level timestamps (requires stable-ts or whisperx installed)
    word_timestamps: bool = True

    # Translation target languages (NLLB-200). Empty list = no translation.
    translate_to: list[str] = ["en"]

    # ML device: "auto" (best available) or specific (cpu/cuda/mps)
    device: str = "auto"

    # Separator model shifts (0 = fast, 5 = quality)
    shifts: int = 0

    # Max upload size
    max_upload_mb: int = 100

    def _resolve_paths(self) -> None:
        root = _project_root()
        default_storage = root / "storage"
        if not self.storage_dir:
            self.storage_dir = str(default_storage)
        if not self.db_path:
            self.db_path = str(default_storage / "compas.db")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings._resolve_paths()
        Path(_settings.storage_dir).mkdir(parents=True, exist_ok=True)
    return _settings
