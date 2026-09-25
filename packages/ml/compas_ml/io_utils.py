"""Audio I/O utilities — load, resample, mono conversion, peak extraction."""
from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf


def load_audio(path: str | Path, target_sr: int = 44100, mono: bool = True) -> Tuple[np.ndarray, int]:
    """Load an audio file. Resamples to target_sr. Optionally downmixes to mono.

    Returns (samples, sample_rate). samples is float32 in [-1, 1].
    """
    y, sr = sf.read(str(path), always_2d=True)
    if y.dtype != np.float32:
        y = y.astype(np.float32)
    if mono:
        y = y.mean(axis=1)  # (n,)
    else:
        y = y.T  # (channels, n)
    if sr != target_sr:
        y = _resample_poly(y, sr, target_sr)
        sr = target_sr
    return y, sr


def _resample_poly(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Polyphase resampling using scipy.signal.resample_poly."""
    from math import gcd

    from scipy.signal import resample_poly

    g = gcd(sr_in, sr_out)
    up = sr_out // g
    down = sr_in // g
    if y.ndim == 1:
        return resample_poly(y, up, down).astype(np.float32)
    return resample_poly(y, up, down, axis=-1).astype(np.float32)


def save_audio(path: str | Path, y: np.ndarray, sr: int, format: str = "flac", subtype: str = "PCM_16") -> None:
    """Save audio. format inferred from suffix if not given."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = format or path.suffix.lstrip(".").lower() or "wav"
    if fmt == "mp3":
        # soundfile doesn't write mp3; fall back to wav with a note
        fmt = "wav"
    sf.write(str(path), y, sr, format=fmt, subtype=subtype)


def probe_duration(path: str | Path) -> float:
    """Use ffprobe for fast duration; fall back to soundfile."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if out.returncode == 0:
            import json as _json

            return float(_json.loads(out.stdout).get("format", {}).get("duration", 0.0))
    except Exception:
        pass
    try:
        info = sf.info(str(path))
        return float(info.frames) / float(info.samplerate)
    except Exception:
        return 0.0


def compute_peaks(
    y: np.ndarray,
    n_peaks: int = 4000,
) -> list[float]:
    """Compute a sparse peak list for waveform rendering (used by the gem grid bg)."""
    if y.size == 0:
        return []
    # Downsample to ~n_peaks buckets, take max abs per bucket
    bucket_size = max(1, y.size // n_peaks)
    n_buckets = y.size // bucket_size
    if n_buckets == 0:
        return [float(abs(y[0]))]
    y2 = y[: n_buckets * bucket_size].reshape(n_buckets, bucket_size)
    peaks = np.max(np.abs(y2), axis=1)
    return [float(p) for p in peaks]


def compute_rms_curve(y: np.ndarray, n_bars: int = 64) -> list[float]:
    """RMS energy per bar (for musicality curves)."""
    if y.size == 0 or n_bars <= 0:
        return []
    bucket = max(1, y.size // n_bars)
    n = y.size // bucket
    if n == 0:
        return [0.0] * n_bars
    y2 = y[: n * bucket].reshape(n, bucket)
    rms = np.sqrt(np.mean(y2.astype(np.float64) ** 2, axis=1))
    # Pad / trim to n_bars
    if len(rms) < n_bars:
        rms = np.concatenate([rms, np.zeros(n_bars - len(rms))])
    return [float(v) for v in rms[:n_bars]]


def safe_filename(name: str) -> str:
    """Make a safe stem for filesystem paths."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
