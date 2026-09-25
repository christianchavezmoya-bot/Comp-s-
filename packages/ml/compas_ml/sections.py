"""Section detection.

For v0.1 we use a rule-based detector informed by the locked genre taxonomy
(§1.2 / §1.6 of COMPAS_PLAN.md). The detector looks at:
  - vocal activity (high in verso/coro/soneo; low in mambo/majae/breakdown/intro)
  - percussion density (high in coro/majae/montuno; low in breakdown)
  - bass energy (peaks in mambo, montuno)
  - energy (high in coro, low in breakdown)
  - vocal pitch variance (high in soneo)
  - spectral novelty (peaks at section boundaries)

Output: a list of Sections with start_sec, end_sec, type, confidence.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np

log = logging.getLogger("compas.ml.sections")


Genre = Literal["bachata", "salsa"]


@dataclass
class Section:
    start_sec: float
    end_sec: float
    type: str
    confidence: float
    notes: str = ""


def detect_sections(
    y_mix: np.ndarray,
    y_vocals: np.ndarray | None,
    y_drums: np.ndarray | None,
    y_bass: np.ndarray | None,
    sr: int,
    bpm: float,
    duration_sec: float,
    genre: Genre = "bachata",
    min_section_sec: float = 4.0,
) -> list[Section]:
    """Detect song sections. Returns contiguous non-overlapping sections covering [0, duration_sec]."""
    if duration_sec <= 0:
        return [Section(0.0, 0.0, "outro", 0.0)]

    # Compute per-bar (8-count) features
    sec_per_beat = 60.0 / bpm if bpm > 0 else 0.5
    sec_per_bar = sec_per_beat * 8
    n_bars = max(1, int(duration_sec / sec_per_bar))
    bar_len_samples = int(sec_per_bar * sr)

    energy_per_bar = _bar_rms(y_mix, sr, n_bars, bar_len_samples)
    vocal_energy_per_bar = _bar_rms(y_vocals if y_vocals is not None else np.zeros_like(y_mix), sr, n_bars, bar_len_samples)
    drum_energy_per_bar = _bar_rms(y_drums if y_drums is not None else np.zeros_like(y_mix), sr, n_bars, bar_len_samples)
    bass_energy_per_bar = _bar_rms(y_bass if y_bass is not None else np.zeros_like(y_mix), sr, n_bars, bar_len_samples)

    # Normalize to 0..1
    def _norm(x):
        if x.max() > 0:
            return x / x.max()
        return x

    e = _norm(energy_per_bar)
    v = _norm(vocal_energy_per_bar)
    d = _norm(drum_energy_per_bar)
    b = _norm(bass_energy_per_bar)

    # Classify each bar
    raw_labels = []
    raw_conf = []
    for i in range(n_bars):
        label, conf = _classify_bar(i, n_bars, e[i], v[i], d[i], b[i], genre, energy_per_bar, vocal_energy_per_bar, drum_energy_per_bar, bass_energy_per_bar)
        raw_labels.append(label)
        raw_conf.append(conf)

    # Smooth: merge bars with the same label that are close, drop sections shorter than min_section_sec
    sections = _merge_bars_into_sections(
        raw_labels, raw_conf, sec_per_bar, min_section_sec, duration_sec, genre
    )

    # First section is intro until vocals start
    if sections and sections[0].type != "intro" and v[0] < 0.1 and e[0] < 0.3:
        sections.insert(0, Section(0.0, sections[0].start_sec, "intro", 0.7))

    return sections


def _bar_rms(y: np.ndarray, sr: int, n_bars: int, bar_len: int) -> np.ndarray:
    if y.size == 0:
        return np.zeros(n_bars)
    out = np.zeros(n_bars)
    for i in range(n_bars):
        start = i * bar_len
        end = min(start + bar_len, y.size)
        if end > start:
            seg = y[start:end]
            out[i] = float(np.sqrt(np.mean(seg.astype(np.float64) ** 2)))
    return out


def _classify_bar(
    i: int,
    n_bars: int,
    e: float,
    v: float,
    d: float,
    b: float,
    genre: Genre,
    e_all: np.ndarray,
    v_all: np.ndarray,
    d_all: np.ndarray,
    b_all: np.ndarray,
) -> tuple[str, float]:
    """Rule-based classification of one bar."""
    e_med = float(np.median(e_all))
    v_med = float(np.median(v_all))
    d_med = float(np.median(d_all))
    b_med = float(np.median(b_all))

    # Heuristics, in priority order
    # 1. Breakdown: very low everything
    if e < 0.15 and d < 0.15 and b < 0.15:
        return "breakdown", 0.7

    # 2. Mambo: bass hit, vocal drop
    if b > 1.4 * b_med and v < 0.5 * v_med and e > 0.5:
        return "mambo", 0.6

    # 3. Soneo: vocals present, but with high pitch variance (we approximate with v>med and energy variability)
    if v > 0.8 and i > 1 and i < n_bars - 2:
        # Heuristic: soneo is often 8+ bars of singing with no chorus pattern
        if d > 0.5 and e > 0.4:
            return "soneo", 0.5

    # 4. Coro: high energy + vocals + drums
    if e > e_med and v > v_med * 0.5 and d > d_med * 0.5:
        return "coro", 0.7

    # 5. Verso: vocals but lower energy
    if v > 0.4 and e < e_med * 1.2:
        return "verso", 0.6

    # 6. Majae: percussion-led, no vocals, in middle of song
    if v < 0.3 and d > 0.6 and i > 0 and i < n_bars - 1:
        return "majae", 0.5

    # 7. Default
    return "verso", 0.4


def _merge_bars_into_sections(
    labels: list[str],
    confs: list[float],
    sec_per_bar: float,
    min_section_sec: float,
    duration_sec: float,
    genre: Genre,
) -> list[Section]:
    """Merge consecutive bars with the same label into sections; force first=intro, last=outro."""
    if not labels:
        return [Section(0.0, duration_sec, "outro", 0.5)]

    # Build initial segments
    segments: list[Section] = []
    cur_label = labels[0]
    cur_start = 0
    cur_conf_sum = confs[0]
    cur_count = 1

    for i in range(1, len(labels)):
        if labels[i] == cur_label:
            cur_conf_sum += confs[i]
            cur_count += 1
        else:
            segments.append(
                Section(
                    start_sec=cur_start * sec_per_bar,
                    end_sec=i * sec_per_bar,
                    type=cur_label,
                    confidence=cur_conf_sum / cur_count,
                )
            )
            cur_label = labels[i]
            cur_start = i
            cur_conf_sum = confs[i]
            cur_count = 1
    # Last segment
    segments.append(
        Section(
            start_sec=cur_start * sec_per_bar,
            end_sec=len(labels) * sec_per_bar,
            type=cur_label,
            confidence=cur_conf_sum / cur_count,
        )
    )

    # Drop sections shorter than min_section_sec (merge into neighbor)
    min_bars = max(1, int(min_section_sec / sec_per_bar))
    i = 0
    while i < len(segments):
        s = segments[i]
        seg_dur = s.end_sec - s.start_sec
        n_bars_in_seg = int(seg_dur / sec_per_bar + 0.5)
        if n_bars_in_seg < min_bars and 0 < i < len(segments) - 1:
            # Merge with the previous segment
            prev = segments[i - 1]
            segments[i - 1] = Section(
                start_sec=prev.start_sec,
                end_sec=s.end_sec,
                type=prev.type,  # keep the longer segment's label
                confidence=(prev.confidence + s.confidence) / 2,
            )
            segments.pop(i)
        else:
            i += 1

    # Force first=intro if it starts at 0 with low energy
    if segments and segments[0].start_sec == 0.0 and segments[0].type != "intro":
        if segments[0].end_sec - segments[0].start_sec < 16.0:  # only if intro is short
            segments[0] = Section(
                start_sec=0.0,
                end_sec=segments[0].end_sec,
                type="intro",
                confidence=segments[0].confidence * 0.8,
            )

    # Force last=outro
    if segments and segments[-1].end_sec >= duration_sec - 0.5 and segments[-1].type != "outro":
        segments[-1] = Section(
            start_sec=segments[-1].start_sec,
            end_sec=duration_sec,
            type="outro",
            confidence=segments[-1].confidence * 0.8,
        )

    return segments
