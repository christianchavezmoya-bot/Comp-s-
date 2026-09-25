"""Beat, tempo, and downbeat detection.

Three methods available:
  - librosa (default, fast, CPU-friendly)
  - essentia (often more accurate for dance music)
  - beat_transformer (SOTA but heavy; aspirational for v0.1)

Output: a dict with `bpm`, `bpm_alt`, `beats` (list of seconds), `downbeats` (list of seconds),
`first_downbeat`, `time_signature`. We also compute an 8-count start for bachata.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Literal

import numpy as np

log = logging.getLogger("compas.ml.beats")


@dataclass
class BeatResult:
    bpm: float
    bpm_alt: list[float]
    bpm_confidence: float  # 0..1
    beats: list[float]
    downbeats: list[float]
    first_downbeat_sec: float
    first_8count_start_sec: float
    time_signature: str  # "4/4" always for our genres
    feel: Literal["single_time", "double_time", "half_time"]
    method: str
    elapsed_sec: float


def detect_beats(
    y: np.ndarray,
    sr: int,
    method: Literal["librosa", "essentia", "auto"] = "auto",
    target_tempo: float | None = None,
) -> BeatResult:
    """Detect beats, downbeats, BPM from a mono audio signal.

    `target_tempo`: optional hint (Bachata ~128, Salsa ~180). If given, we prefer that
    tempo if it's within 10% of the detected one.
    """
    import time as _time

    t0 = _time.time()

    if method == "auto":
        method = "librosa"  # safe default for v0.1; essentia sometimes misreads bachata

    if method == "librosa":
        result = _librosa_beats(y, sr, target_tempo=target_tempo)
    elif method == "essentia":
        result = _essentia_beats(y, sr)
    else:
        raise ValueError(f"Unknown beat method: {method}")

    result.elapsed_sec = _time.time() - t0
    return result


def _librosa_beats(y: np.ndarray, sr: int, target_tempo: float | None = None) -> BeatResult:
    import librosa

    # Onset envelope
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)

    # Tempo
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=512)
    # librosa returns tempo as a numpy scalar
    bpm = float(np.asarray(tempo).item())
    bpm_alt = []

    # If we have a target, snap to it within tolerance
    if target_tempo is not None and 60 < target_tempo < 220:
        if abs(bpm - target_tempo) / target_tempo > 0.10:
            # Try doubling/halving
            for cand in (bpm * 2, bpm / 2):
                if abs(cand - target_tempo) / target_tempo < 0.10:
                    bpm_alt.append(bpm)
                    bpm = cand
                    # Re-detect with new tempo
                    tempo, beats = librosa.beat.beat_track(
                        onset_envelope=onset_env, sr=sr, hop_length=512, bpm=cand
                    )
                    bpm = float(np.asarray(tempo).item())
                    break

    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512).tolist()

    # Downbeats: every 4 beats starting from the first beat (assuming 4/4)
    downbeats = beat_times[::4] if len(beat_times) >= 4 else beat_times

    # 8-count: every 8 beats
    eight_count_starts = beat_times[::8] if len(beat_times) >= 8 else beat_times

    # Feel detection
    if bpm < 110:
        feel = "half_time"
    elif bpm > 160:
        feel = "single_time"  # salsa actually counts half-tempo
    else:
        feel = "double_time"  # bachata: reported BPM is the "true" tempo (kick on 1 and 5)

    # Confidence: 0.5 base, +0.5 if BPM is in a "reasonable" range for our genres
    confidence = 0.5
    if 80 <= bpm <= 230:
        confidence += 0.3
    if target_tempo is not None and abs(bpm - target_tempo) / target_tempo < 0.05:
        confidence = min(1.0, confidence + 0.2)

    return BeatResult(
        bpm=bpm,
        bpm_alt=bpm_alt,
        bpm_confidence=confidence,
        beats=beat_times,
        downbeats=downbeats,
        first_downbeat_sec=beat_times[0] if beat_times else 0.0,
        first_8count_start_sec=eight_count_starts[0] if eight_count_starts else 0.0,
        time_signature="4/4",
        feel=feel,
        method="librosa",
        elapsed_sec=0.0,
    )


def _essentia_beats(y: np.ndarray, sr: int) -> BeatResult:
    """Essentia RhythmExtractor2013 — often more accurate for dance music."""
    import essentia.standard as es
    import time as _time

    t0 = _time.time()
    # Essentia wants float32
    y32 = y.astype(np.float32) if y.dtype != np.float32 else y
    extractor = es.RhythmExtractor2013(method="degara")
    bpm, ticks, confidence, _, _ = extractor(y32)
    beat_times = [float(t) for t in ticks]

    downbeats = beat_times[::4] if len(beat_times) >= 4 else beat_times
    eight_count_starts = beat_times[::8] if len(beat_times) >= 8 else beat_times

    if bpm < 110:
        feel = "half_time"
    elif bpm > 160:
        feel = "single_time"
    else:
        feel = "double_time"

    return BeatResult(
        bpm=float(bpm),
        bpm_alt=[],
        bpm_confidence=float(confidence),
        beats=beat_times,
        downbeats=downbeats,
        first_downbeat_sec=beat_times[0] if beat_times else 0.0,
        first_8count_start_sec=eight_count_starts[0] if eight_count_starts else 0.0,
        time_signature="4/4",
        feel=feel,
        method="essentia",
        elapsed_sec=_time.time() - t0,
    )


def validate_8count(
    beats: list[float],
    bpm: float,
    req_onsets: list[float] | None = None,
    bongo_onsets: list[float] | None = None,
    search_window_sec: float = 0.25,
) -> tuple[int, float, float]:
    """Pick the best 8-count phase given BPM and (optional) instrument onsets.

    Returns: (best_bar_index, confidence, phase_offset_sec).
    `best_bar_index` is the bar number (0-indexed) where beat 1 of the 8-count lands.
    `phase_offset_sec` is the offset from `beats[0]` to the chosen downbeat.

    For bachata: requinto onset should land on beat 1; bongó on every 8th-note subdivision.
    """
    if not beats or bpm <= 0:
        return 0, 0.0, 0.0

    sec_per_beat = 60.0 / bpm
    sec_per_8count = sec_per_beat * 8

    best_score = -1.0
    best_offset = 0.0
    best_bar = 0

    # Try shifts from -search_window to +search_window
    n_steps = 32
    offsets = np.linspace(-search_window_sec, search_window_sec, n_steps)

    # If we have requinto onsets, score each candidate phase by how many onsets land near
    # beats 1 / 3 / 5 / 7 (every 2 beats) of the 8-count.
    if req_onsets:
        req_arr = np.array(req_onsets)
        for off in offsets:
            score = 0.0
            for bar_idx in range(8):
                bar_t0 = beats[0] + bar_idx * sec_per_8count + off
                # Beat 1, 3, 5, 7 of this bar
                for beat_in_bar in (0, 2, 4, 6):
                    target_t = bar_t0 + beat_in_bar * sec_per_beat
                    # Closest requinto onset within 0.1s
                    closest = np.min(np.abs(req_arr - target_t))
                    if closest < 0.1:
                        score += 1.0 - (closest / 0.1)
            if score > best_score:
                best_score = score
                best_offset = float(off)
                best_bar = 0
    else:
        # No requinto onsets — fall back to the first downbeat being the 8-count start
        best_offset = 0.0
        best_score = 0.5
        best_bar = 0

    # Confidence scales with score
    confidence = min(1.0, best_score / 8.0) if req_onsets else 0.5
    return best_bar, confidence, best_offset
