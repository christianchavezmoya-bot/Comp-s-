"""Salsa per-stem split: from Demucs's 4 stems (vocals/drums/bass/other) to 9-10 salsa stems.

For salsa, the locked taxonomy (§1.5 of COMPAS_PLAN.md) is:
  vocals-lead, vocals-coro, piano, bass, congas, timbales+cowbell, bongo, clave, maracas+guiro, horns

Demucs gives us:
  vocals  → vocals-lead + vocals-coro
  drums   → congas + timbales + bongo + (cowbell mounts on timbales)
  bass    → bass
  other   → piano + clave + horns + maracas+guiro

We further split each Demucs stem using:
  - Frequency-band energy ratios
  - Onset-density per band
  - Spectral centroid (per hit)
  - Harmonicity (HPSS)

For v0.2 we use band + onset heuristics (fast, no extra model).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

log = logging.getLogger("compas.ml.stemsplit")


@dataclass
class StemSplit:
    """Output of salsa stem splitting. All are mono float32 at the same sample rate."""
    vocals_lead: np.ndarray | None = None
    vocals_coro: np.ndarray | None = None
    piano: np.ndarray | None = None
    bass: np.ndarray | None = None
    congas: np.ndarray | None = None
    timbales_cowbell: np.ndarray | None = None
    bongo: np.ndarray | None = None
    clave: np.ndarray | None = None
    maracas_guiro: np.ndarray | None = None
    horns: np.ndarray | None = None


def _bandpass(y: np.ndarray, sr: int, low: float, high: float) -> np.ndarray:
    """Zero-phase Butterworth bandpass."""
    from scipy.signal import butter, sosfiltfilt

    nyq = sr / 2
    low_n = max(low / nyq, 1e-5)
    high_n = min(high / nyq, 0.99999)
    if high_n <= low_n:
        return np.zeros_like(y)
    sos = butter(4, [low_n, high_n], btype="band", output="sos")
    return sosfiltfilt(sos, y).astype(np.float32)


def _highpass(y: np.ndarray, sr: int, low: float) -> np.ndarray:
    from scipy.signal import butter, sosfiltfilt

    nyq = sr / 2
    sos = butter(4, low / nyq, btype="highpass", output="sos")
    return sosfiltfilt(sos, y).astype(np.float32)


def _lowpass(y: np.ndarray, sr: int, high: float) -> np.ndarray:
    from scipy.signal import butter, sosfiltfilt

    nyq = sr / 2
    sos = butter(4, high / nyq, btype="lowpass", output="sos")
    return sosfiltfilt(sos, y).astype(np.float32)


def split_salsa_stems(
    vocals: np.ndarray | None,
    drums: np.ndarray | None,
    bass: np.ndarray | None,
    other: np.ndarray | None,
    sr: int,
) -> StemSplit:
    """Take Demucs's 4 stems and return the salsa 10-stem split."""
    out = StemSplit(bass=bass)

    if vocals is not None and vocals.size > 0:
        # Lead vs coro: lead tends to be 200-2000 Hz, coro higher and less pitched
        # Simple approach: lead = bandpassed 100-3000 Hz, coro = residual
        lead = _bandpass(vocals, sr, 100, 3000)
        coro = vocals - lead
        # Normalize to similar RMS
        if np.sqrt(np.mean(lead ** 2)) > 0:
            out.vocals_lead = lead
        if np.sqrt(np.mean(coro ** 2)) > 0:
            out.vocals_coro = coro.astype(np.float32)

    if drums is not None and drums.size > 0:
        # Frequency ranges (very approximate):
        #   bongó:    200-1500 Hz (high-pitched, small drums)
        #   congas:   60-400 Hz (mid, open tones)
        #   timbales: 100-3000 Hz (wide range)
        #   cowbell:  500-2000 Hz (metallic, attached to timbales)
        # Heuristic split:
        bongo = _bandpass(drums, sr, 200, 1500)
        congas = _bandpass(drums, sr, 60, 400)
        timbales = drums - bongo - congas  # residual
        # Apply some shaping
        if np.sqrt(np.mean(bongo ** 2)) > 1e-6:
            out.bongo = bongo
        if np.sqrt(np.mean(congas ** 2)) > 1e-6:
            out.congas = congas
        if np.sqrt(np.mean(timbales ** 2)) > 1e-6:
            out.timbales_cowbell = timbales.astype(np.float32)

    if other is not None and other.size > 0:
        # Clave: very short clicks, 1000-4000 Hz, transient
        # Piano: 27-4200 Hz, harmonic
        # Horns: 200-2000 Hz, sustained
        # Maracas/güiro: noise, very high
        clave = _bandpass(other, sr, 1000, 5000)
        # Maracas/güiro: very high noise
        maracas_guiro = _highpass(other, sr, 5000)
        # Piano + horns: the residual harmonic content
        piano_horns = other - clave - maracas_guiro
        # Split piano from horns by energy in different bands
        # Piano: more energy in 100-1000; horns: 200-2000 with strong 1-2kHz
        piano = _bandpass(piano_horns, sr, 27, 1200)
        horns = piano_horns - piano

        if np.sqrt(np.mean(clave ** 2)) > 1e-6:
            out.clave = clave
        if np.sqrt(np.mean(maracas_guiro ** 2)) > 1e-6:
            out.maracas_guiro = maracas_guiro.astype(np.float32)
        if np.sqrt(np.mean(piano ** 2)) > 1e-6:
            out.piano = piano
        if np.sqrt(np.mean(horns ** 2)) > 1e-6:
            out.horns = horns.astype(np.float32)

    log.info(
        "Salsa stem split: %s",
        {k: v.shape for k, v in out.__dict__.items() if v is not None},
    )
    return out


def split_bachata_stems(
    vocals: np.ndarray | None,
    drums: np.ndarray | None,
    bass: np.ndarray | None,
    other: np.ndarray | None,
    sr: int,
) -> dict[str, np.ndarray]:
    """Bachata 7-stem split.

    vocals → vocals-lead + vocals-back
    other  → requinto + segunda + (residual = synth/piano if present)
    bass   → bass
    drums  → bongo (with timbales residual)
    """
    out: dict[str, np.ndarray] = {"bass": bass} if bass is not None else {}

    if vocals is not None and vocals.size > 0:
        lead = _bandpass(vocals, sr, 100, 3000)
        back = vocals - lead
        if np.sqrt(np.mean(lead ** 2)) > 1e-6:
            out["vocals_lead"] = lead
        if np.sqrt(np.mean(back ** 2)) > 1e-6:
            out["vocals_back"] = back.astype(np.float32)

    if drums is not None and drums.size > 0:
        # Bongó is the dominant percussion in bachata. Use 200-1500 Hz band.
        bongo = _bandpass(drums, sr, 200, 1500)
        if np.sqrt(np.mean(bongo ** 2)) > 1e-6:
            out["bongo"] = bongo
        # Güira is high-frequency metallic scrape > 4000 Hz
        guira = _highpass(drums, sr, 4000)
        if np.sqrt(np.mean(guira ** 2)) > 1e-6:
            out["guira"] = guira.astype(np.float32)

    if other is not None and other.size > 0:
        # Requinto: lead melodic guitar, 250 Hz - 4 kHz
        requinto = _bandpass(other, sr, 250, 4000)
        # Segunda: rhythm guitar, 80-250 Hz
        segunda = _bandpass(other, sr, 80, 250)
        if np.sqrt(np.mean(requinto ** 2)) > 1e-6:
            out["requinto"] = requinto
        if np.sqrt(np.mean(segunda ** 2)) > 1e-6:
            out["segunda"] = segunda.astype(np.float32)
        # Residual = synth/piano/other melodic
        residual = other - requinto - segunda
        if np.sqrt(np.mean(residual ** 2)) > 1e-6:
            out["synth"] = residual.astype(np.float32)

    log.info("Bachata stem split: %d stems", len(out))
    return out
