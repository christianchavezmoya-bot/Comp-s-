"""ML pipeline config — knobs that control model selection, device, and quality."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class PipelineConfig:
    """All knobs the user (or Admin) can change to trade off speed vs quality."""

    # Stem separation
    separator: Literal["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_q", "none"] = "htdemucs"
    separator_device: Literal["cpu", "cuda", "mps"] = "cpu"
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
    whisper_device: str = "cpu"
    translate_to: list[str] = field(default_factory=lambda: ["en"])

    # Models cache
    model_cache_dir: str = os.environ.get("COMPAS_MODEL_CACHE", str(Path.home() / ".cache" / "compas" / "models"))

    # Storage layout
    stems_format: Literal["flac", "wav", "mp3"] = "flac"
    stems_sample_rate: int = 44100

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
