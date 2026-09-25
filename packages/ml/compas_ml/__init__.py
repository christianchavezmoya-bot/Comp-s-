"""Compás ML package — model runners for stem separation, beat detection, and lyrics.

In v0.1 this is a thin scaffold. Real implementations land in Phase 1.
"""
from __future__ import annotations

__version__ = "0.1.0"


def get_pipeline_stages() -> list[str]:
    """Returns the ordered list of pipeline stages.

    Each stage has a corresponding module in this package:
      1. preflight       - format check, loudness normalization
      2. separation      - Demucs v4 htdemucs_ft + Mel-Band-Roformer ensemble
      3. beats           - Beat-Transformer
      4. eight_count     - bachata 8-count validator
      5. structure       - SA3 + custom rules
      6. vocals          - Whisper large-v3 + pyin pitch
      7. musicality      - onset density, energy, flux, drops
      8. validate        - SDR / WER / F1 sanity check
    """
    return [
        "preflight",
        "separation",
        "beats",
        "eight_count",
        "structure",
        "vocals",
        "musicality",
        "validate",
    ]
