"""Stem separation via Demucs.

For v0.1 (CPU-only, no GPU), we use htdemucs (4-stem: vocals/drums/bass/other).
For higher quality, htdemucs_ft is the fine-tuned variant; it gives ~1-2 dB more SDR.

Output: per-stem FLAC files + a numpy array per stem for downstream analysis.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from compas_ml.config import PipelineConfig
from compas_ml.io_utils import load_audio, save_audio

log = logging.getLogger("compas.ml.separation")


@dataclass
class SeparationResult:
    stems: dict[str, np.ndarray]  # stem_name -> mono float32
    sr: int
    duration_sec: float
    model: str
    elapsed_sec: float
    sdr_estimates: dict[str, float]  # rough quality estimate per stem


# Demucs canonical stems: vocals, drums, bass, other
# After we get {vocals, drums, bass, other}, we further split using onset classifiers
# (see compas_ml.onsets). For now, we keep the 4 Demucs stems as our ground truth.
DEMUCS_STEMS = ("vocals", "drums", "bass", "other")


def _import_demucs():
    try:
        import demucs.api  # noqa
        import demucs.pretrained  # noqa

        return demucs
    except ImportError as e:
        raise RuntimeError(
            "demucs is not installed. Run: pip install demucs\n"
            "(torch + torchaudio must also be installed)"
        ) from e


def separate(
    source_path: str | Path,
    out_dir: str | Path,
    config: PipelineConfig | None = None,
) -> SeparationResult:
    """Separate an audio file into 4 stems (vocals/drums/bass/other).

    Args:
        source_path: input audio file (any format soundfile/ffmpeg can read)
        out_dir: directory to write FLAC stems into
        config: pipeline config (defaults to DEFAULT)

    Returns:
        SeparationResult with stems, sr, duration, model, elapsed_sec
    """
    config = config or PipelineConfig()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    log.info("Separating %s with %s on %s", source_path, config.separator, config.separator_device)

    if config.separator == "none":
        return _passthrough_separation(source_path, out_dir, config, t0)

    demucs = _import_demucs()

    # Load as stereo for Demucs (it expects (channels, samples))
    y, sr = load_audio(source_path, target_sr=44100, mono=False)
    if y.ndim == 1:
        # Mono source — duplicate to stereo
        y = np.stack([y, y], axis=0)
    if y.shape[0] == 1:
        # Mono after read — duplicate to stereo
        y = np.concatenate([y, y], axis=0)
    duration = y.shape[1] / sr

    # Use demucs Separator API (string-name based; it loads the model itself)
    from demucs.separate import Separator

    separator = Separator(
        model=config.separator,
        device=config.separator_device,
        segment=config.segment_length,
        overlap=config.overlap,
        jobs=config.separator_jobs,
        shifts=config.separator_shifts,
        progress=False,
    )

    # Demucs `separate_tensor` expects (channels, samples) — 2D
    import torch

    wav = torch.from_numpy(y).float().to(config.separator_device)

    with torch.no_grad():
        # returns (wav_tensor, {stem_name: (channels, samples)})
        _, stem_dict = separator.separate_tensor(wav)

    source_names = separator.model.sources  # ['vocals', 'drums', 'bass', 'other']

    # Convert each stem's tensor to a numpy array (mono)
    stems_tensors: dict[str, torch.Tensor] = stem_dict

    stems_mono: dict[str, np.ndarray] = {}
    for name in source_names:
        stem_tensor = stems_tensors[name]  # (channels, samples)
        # Average to mono
        stem = stem_tensor.mean(dim=0).cpu().numpy().astype(np.float32)
        stems_mono[name] = stem
        # Save FLAC
        save_audio(out_dir / f"{name}.{config.stems_format}", stem, sr, format=config.stems_format)

    # Rough SDR estimate via residual: a stem that explains a lot of energy from the mix
    # is a "good" stem. We don't have ground truth so this is just energy ratio.
    mix = y.mean(axis=0)
    sdr_estimates = {}
    for name, stem in stems_mono.items():
        if np.sum(mix ** 2) > 0:
            sdr_estimates[name] = float(
                10 * np.log10(
                    np.sum(stem ** 2) / max(np.sum(mix ** 2) - np.sum(stem ** 2), 1e-10)
                )
            )
        else:
            sdr_estimates[name] = 0.0

    elapsed = time.time() - t0
    log.info("Separation done in %.1fs → %d stems in %s", elapsed, len(stems_mono), out_dir)

    return SeparationResult(
        stems=stems_mono,
        sr=sr,
        duration_sec=duration,
        model=config.separator,
        elapsed_sec=elapsed,
        sdr_estimates=sdr_estimates,
    )


def _passthrough_separation(
    source_path: str | Path,
    out_dir: Path,
    config: PipelineConfig,
    t0: float,
) -> SeparationResult:
    """Stub separation: just load the mix and put it in 'other' for testing."""
    y, sr = load_audio(source_path, target_sr=44100, mono=True)
    save_audio(out_dir / f"other.{config.stems_format}", y, sr, format=config.stems_format)
    return SeparationResult(
        stems={"other": y},
        sr=sr,
        duration_sec=float(len(y) / sr),
        model="passthrough",
        elapsed_sec=time.time() - t0,
        sdr_estimates={"other": 0.0},
    )
