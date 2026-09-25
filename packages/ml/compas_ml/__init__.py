"""Compás ML package — model runners for stem separation, beat detection, and lyrics.

Public API:
  - compas_ml.pipeline.run_pipeline: run the full analysis on one audio file
  - compas_ml.separation.separate: just the stem separation stage
  - compas_ml.beats.detect_beats: just the beat detection stage
  - compas_ml.sections.detect_sections: just the section detection stage
  - compas_ml.clave.detect_clave: just the clave detection stage (salsa)
  - compas_ml.onsets.detect_onsets: per-stem onset detection
"""
from __future__ import annotations

__version__ = "0.2.0"


def get_pipeline_stages() -> list[str]:
    return [
        "preflight",
        "separation",
        "beats",
        "eight_count",
        "structure",
        "clave",
        "musicality",
        "validate",
    ]
