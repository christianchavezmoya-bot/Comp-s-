"""Onset detection per stem.

For the gem-grid, we want: per-stem, a list of (time_sec, pitch_midi, strength) events.

Demucs gives us 4 stems: vocals, drums, bass, other. We further split `drums` and `other`
using simple frequency-band + onset-DNN heuristics, but for v0.1 we use onset detection
on the raw stems and pitch estimation for the pitched ones.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

log = logging.getLogger("compas.ml.onsets")


@dataclass
class Onset:
    time_sec: float
    pitch_midi: int | None  # None if unpitched
    strength: float
    is_hit: bool


def detect_onsets(
    y: np.ndarray,
    sr: int,
    hop_length: int = 512,
    min_strength: float = 0.05,
) -> list[Onset]:
    """Detect onsets using librosa, with a coarse pitch estimate from spectral centroid.

    For now this is one onset set per audio; for per-stem onsets, call this on each stem.
    """
    import librosa

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        units="frames",
        backtrack=False,
        delta=0.1,
        wait=10,
    )
    if len(onset_frames) == 0:
        return []

    times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
    strengths = onset_env[onset_frames]

    # Normalize strengths to 0..1
    if strengths.max() > 0:
        norm = strengths / strengths.max()
    else:
        norm = strengths

    # Estimate pitch from spectral centroid
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    # Centroid in Hz → rough MIDI: midi = 69 + 12 * log2(cent / 440)
    cent_at_onsets = cent[onset_frames]
    pitches_midi = np.where(
        cent_at_onsets > 0,
        69 + 12 * np.log2(cent_at_onsets / 440.0 + 1e-10),
        60,
    ).astype(int)

    onsets = []
    for i, t in enumerate(times):
        s = float(norm[i])
        if s < min_strength:
            continue
        is_hit = s > 0.85  # top 15% are "hits"
        onsets.append(
            Onset(
                time_sec=float(t),
                pitch_midi=int(pitches_midi[i]),
                strength=s,
                is_hit=is_hit,
            )
        )
    return onsets


def detect_pitch_onsets(y: np.ndarray, sr: int, fmin: float = 60.0, fmax: float = 2000.0) -> list[Onset]:
    """Pitch-tracked onsets via librosa.pyin. For vocals or pitched instruments."""
    import librosa

    f0, voiced_flag, voiced_prob = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, hop_length=512, fill_na=np.nan
    )
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=512)
    onsets: list[Onset] = []
    prev_pitch = np.nan
    for t, f, v in zip(times, f0, voiced_flag):
        if not v or np.isnan(f):
            prev_pitch = np.nan
            continue
        # Note onset when pitch appears or jumps significantly
        if np.isnan(prev_pitch) or abs(f - prev_pitch) > 1.0:
            midi = int(round(69 + 12 * np.log2(f / 440.0)))
            onsets.append(
                Onset(
                    time_sec=float(t),
                    pitch_midi=midi,
                    strength=0.7,
                    is_hit=False,
                )
            )
        prev_pitch = f
    return onsets
