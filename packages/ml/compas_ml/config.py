"""ML pipeline config — knobs that control model selection, device, and quality."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


def detect_best_device() -> str:
    """Return the best available device: 'cuda' → 'mps' → 'cpu'."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        # Apple Silicon (MPS) — torch >= 1.12
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


@dataclass
class PipelineConfig:
    """All knobs the user (or Admin) can change to trade off speed vs quality."""

    # Stem separation
    separator: Literal["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_q", "none"] = "htdemucs"
    separator_device: str = field(default_factory=detect_best_device)
    separator_jobs: int = 2  # parallel jobs; CPU only
    separator_shifts: int = 0  # random shifts for test-time aug; 0 = fast
    segment_length: int = 7  # demucs segment length in seconds
    overlap: float = 0.25  # overlap between segments

    # Beat / BPM
    beats_method: Literal["librosa", "beat_transformer", "essentia"] = "librosa"
    beats_model: str = "htdemucs"  # for beat-transformer (not used yet)

    # Section detection
    section_method: Literal["rules", "sa3", "hybrid"] = "rules"
    min_section_sec: float = 4.0

    # 8-count / phase
    validate_8count: bool = True
    phase_search_window_sec: float = 0.25

    # Clave (salsa only)
    detect_clave: bool = True

    # Vocals / lyrics
    transcribe: bool = True
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v3"] = "base"
    whisper_device: str = field(default_factory=detect_best_device)
    translate_to: list[str] = field(default_factory=lambda: ["en"])
    word_level_timestamps: bool = True  # use stable-ts / whisperx for word timestamps when available
    translation_model: str = "nllb-200-distilled-600M"

    # Models cache
    model_cache_dir: str = os.environ.get(
        "COMPAS_MODEL_CACHE", str(Path.home() / ".cache" / "compas" / "models")
    )

    # Storage layout
    stems_format: Literal["flac", "wav", "mp3"] = "flac"
    stems_sample_rate: int = 44100

    @property
    def device_info(self) -> dict:
        """Return device info for the UI / logs."""
        import torch

        if self.separator_device == "cuda" and torch.cuda.is_available():
            return {
                "device": "cuda",
                "name": torch.cuda.get_device_name(0),
                "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
            }
        if self.separator_device == "mps":
            return {"device": "mps", "name": "Apple Silicon", "memory_gb": "shared"}
        return {"device": "cpu", "name": "CPU", "cores": os.cpu_count()}

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Build a config from environment variables."""
        return cls(
            separator=os.environ.get("COMPAS_SEPARATOR", "htdemucs"),
            separator_device=os.environ.get("COMPAS_DEVICE") or detect_best_device(),
            separator_shifts=int(os.environ.get("COMPAS_SHIFTS", "0")),
            separator_jobs=int(os.environ.get("COMPAS_JOBS", "2")),
            beats_method=os.environ.get("COMPAS_BEATS_METHOD", "librosa"),
            transcribe=os.environ.get("COMPAS_TRANSCRIBE", "false").lower() == "true",
            whisper_model=os.environ.get("COMPAS_WHISPER_MODEL", "base"),
            word_level_timestamps=os.environ.get("COMPAS_WORD_TIMESTAMPS", "true").lower() == "true",
        )

    @property
    def fast_preset(self) -> "PipelineConfig":
        """Speed-first preset for preview/iteration."""
        return PipelineConfig(
            separator="htdemucs",
            separator_shifts=0,
            segment_length=7,
            overlap=0.10,
            beats_method="librosa",
            section_method="rules",
            transcribe=False,
            whisper_model="tiny",
        )

    @property
    def quality_preset(self) -> "PipelineConfig":
        """Quality-first preset for final analysis."""
        return PipelineConfig(
            separator="htdemucs_ft",
            separator_shifts=5,
            segment_length=7,
            overlap=0.25,
            beats_method="librosa",  # beat-transformer still aspirational
            section_method="rules",
            transcribe=True,
            whisper_model="base",
        )


DEFAULT = PipelineConfig()

