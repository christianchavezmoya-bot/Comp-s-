"""Clave detection for salsa.

Detects whether the song is in 2-3 or 3-2 son clave, with confidence.
We look at onset patterns in the drums/percussion stem and check which clave
hypothesis has the best fit over a sliding window.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

log = logging.getLogger("compas.ml.clave")


@dataclass
class ClaveResult:
    direction: str  # "son_2_3", "son_3_2", "rumba_2_3", "rumba_3_2", "none", "unclear"
    confidence: float
    switches: list[dict]  # [{bar, from, to}]


# Son clave pattern in 16th notes of one bar of 4/4: hits at positions
# 0, 6, 10, 14, 16+3 = 19 -> normalized to [0, 0.375, 0.625, 0.875, 1.125]
# 2-3 son clave: hits at 0, 1.5, 3, 4.5, 6 (in 8th-note grid: 1, 1.5, 3, 4.5, 6 / 8)
# A more common reference: 2-3 son clave over 2 bars of 4/4:
# Bar 1: hits on 1, 1-a, 2-&, 3-&
# Bar 2: hit on 4-&
# i.e. pattern = [0, 0.75, 2.5, 3.5, 6.5] in 8-beats-of-16th-notes

SON_CLAVE_2_3 = np.array([0, 0.75, 2.5, 3.5, 6.5]) / 8.0  # normalized to [0, 1] over 2 bars
SON_CLAVE_3_2 = np.array([0, 0.75, 2.5, 5.5, 6.5]) / 8.0  # 3-2 direction


def detect_clave(
    y_drums: np.ndarray,
    y_bass: np.ndarray,
    sr: int,
    bpm: float,
    duration_sec: float,
) -> ClaveResult:
    """Detect the clave direction by correlating drum onsets with each hypothesis.

    Returns the best-matching direction with confidence, plus any mid-song switches.
    """
    if bpm <= 0 or duration_sec < 4:
        return ClaveResult(direction="unclear", confidence=0.0, switches=[])

    import librosa

    onset_env = librosa.onset.onset_strength(y=y_drums, sr=sr, hop_length=512)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, hop_length=512, units="frames", delta=0.1
    )
    if len(onset_frames) < 8:
        return ClaveResult(direction="unclear", confidence=0.0, switches=[])

    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)

    # Two-bar window for clave = 2 bars = 16 beats
    sec_per_beat = 60.0 / bpm
    sec_per_window = sec_per_beat * 16  # 2 bars

    # Slide a window over the song
    window_starts = np.arange(0, max(0.01, duration_sec - sec_per_window), sec_per_window / 2)
    scores_2_3 = []
    scores_3_2 = []
    for ws in window_starts:
        we = ws + sec_per_window
        # Onsets in this window
        mask = (onset_times >= ws) & (onset_times < we)
        local = onset_times[mask] - ws
        # Normalize local time to [0, 1] over the 2-bar window
        local_norm = local / sec_per_window
        # Score each hypothesis: how many onsets fall within tolerance of each clave hit
        def _score(pattern):
            s = 0.0
            for hit in pattern:
                distances = np.abs(local_norm - hit)
                # Account for wrap-around
                distances = np.minimum(distances, 1.0 - distances)
                closest = distances.min() if len(distances) else 1.0
                if closest < 0.05:
                    s += 1.0
            return s

        scores_2_3.append(_score(SON_CLAVE_2_3))
        scores_3_2.append(_score(SON_CLAVE_3_2))

    scores_2_3 = np.array(scores_2_3)
    scores_3_2 = np.array(scores_3_2)
    total = scores_2_3 + scores_3_2
    if (total > 0).sum() == 0:
        return ClaveResult(direction="unclear", confidence=0.0, switches=[])

    # Per-window winner
    winners = np.where(scores_2_3 >= scores_3_2, "son_2_3", "son_3_2")
    # Overall
    final = "son_2_3" if scores_2_3.sum() >= scores_3_2.sum() else "son_3_2"
    confidence = float(max(scores_2_3.sum(), scores_3_2.sum()) / max(1.0, total.sum()))

    # Switches
    switches = []
    for i in range(1, len(winners)):
        if winners[i] != winners[i - 1]:
            switches.append(
                {
                    "start_sec": float(window_starts[i]),
                    "from": winners[i - 1],
                    "to": winners[i],
                }
            )

    if confidence < 0.4:
        return ClaveResult(direction="unclear", confidence=confidence, switches=switches)

    return ClaveResult(direction=final, confidence=confidence, switches=switches)
