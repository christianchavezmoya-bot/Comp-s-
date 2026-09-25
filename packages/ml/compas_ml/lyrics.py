"""Lyrics transcription via OpenAI Whisper.

For v0.1 we use the 'base' model on CPU. Word-level alignment is approximated by
chopping segments into equal-duration words. Real word-level alignment (WhisperX) is
planned for Phase 1.5.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from compas_ml.io_utils import load_audio

log = logging.getLogger("compas.ml.lyrics")


@dataclass
class LyricLine:
    start_sec: float
    end_sec: float
    text: str
    vocal_type: str  # "lead", "backing", "coro", "soneo", "spoken"
    confidence: float


@dataclass
class LyricsResult:
    language: str
    lines: list[LyricLine]
    elapsed_sec: float


def transcribe(
    y: np.ndarray,
    sr: int,
    model_name: str = "base",
    device: str = "cpu",
) -> LyricsResult:
    """Transcribe a vocal stem (or the mix) to text with timestamps."""
    import whisper

    t0 = time.time()
    log.info("Loading Whisper model '%s' on %s (first run downloads ~140MB)", model_name, device)
    model = whisper.load_model(model_name, device=device)
    log.info("Whisper loaded; transcribing")

    # Whisper expects float32 16kHz mono
    if sr != 16000:
        from scipy.signal import resample_poly
        y16 = resample_poly(y, 16000, sr).astype(np.float32)
        sr_use = 16000
    else:
        y16 = y.astype(np.float32)
        sr_use = sr

    # Pad/trim to 30s
    audio = whisper.pad_or_trim(y16)
    result = whisper.transcribe(
        model,
        audio,
        language=None,  # auto-detect
        verbose=False,
        word_timestamps=True,
    )

    lines: list[LyricLine] = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if not text:
            continue
        lines.append(
            LyricLine(
                start_sec=float(seg.get("start", 0.0)),
                end_sec=float(seg.get("end", 0.0)),
                text=text,
                vocal_type="lead",  # TODO: classify lead/backing/coro/soneo
                confidence=float(seg.get("avg_logprob", 0.0)),
            )
        )

    elapsed = time.time() - t0
    log.info("Whisper done in %.1fs: %d lines, language=%s", elapsed, len(lines), result.get("language", "?"))
    return LyricsResult(
        language=result.get("language", "unknown"),
        lines=lines,
        elapsed_sec=elapsed,
    )
