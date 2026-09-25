"""The full Compás analysis pipeline.

Stage order:
  1. Preflight      - format check, loudness normalization, duration
  2. Separation     - Demucs htdemucs → 4 stems (vocals, drums, bass, other)
  3. Beats          - librosa → BPM, beats, downbeats
  4. 8-count        - validate 8-count phase
  5. Structure      - rule-based section detection
  6. Clave          - salsa only, detect 2-3 vs 3-2
  7. Musicality     - compute energy, onset density, bass, vocal curves
  8. Validate       - check SDR, flag low-confidence

Each stage writes a partial result; the orchestrator merges into a final SongAnalysis dict
that matches the TypeScript types in @compas/shared-types.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from compas_ml.beats import detect_beats, validate_8count
from compas_ml.clave import detect_clave
from compas_ml.config import PipelineConfig
from compas_ml.io_utils import load_audio, compute_rms_curve, safe_filename
from compas_ml.onsets import detect_onsets
from compas_ml.separation import separate
from compas_ml.sections import detect_sections, Genre

log = logging.getLogger("compas.ml.pipeline")


def run_pipeline(
    source_path: str | Path,
    out_dir: str | Path,
    genre: Genre = "bachata",
    config: PipelineConfig | None = None,
) -> dict[str, Any]:
    """Run the full analysis pipeline on one audio file. Returns the analysis dict."""
    config = config or PipelineConfig()
    source_path = Path(source_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}
    t_start = time.time()

    # 1. Preflight
    log.info("=== Preflight ===")
    from compas_ml.io_utils import probe_duration

    duration = probe_duration(source_path)
    if duration <= 0:
        raise ValueError(f"Could not read duration of {source_path}")
    log.info("duration: %.1fs", duration)

    # 2. Stem separation
    log.info("=== Stem separation (%s) ===", config.separator)
    t = time.time()
    sep = separate(source_path, out_dir / "stems", config=config)
    timings["separation"] = time.time() - t
    log.info("separation: %.1fs, stems=%s", timings["separation"], list(sep.stems.keys()))

    # Load the mix
    mix, sr = load_audio(source_path, target_sr=44100, mono=True)
    if sr != sep.sr:
        log.warning("sample rate mismatch: %d vs %d", sr, sep.sr)

    # 3. Beats
    log.info("=== Beat detection ===")
    t = time.time()
    target_tempo = 128.0 if genre == "bachata" else 90.0  # salsa half-tempo hint
    beats = detect_beats(sep.stems.get("other", mix), sep.sr, target_tempo=target_tempo)
    timings["beats"] = time.time() - t
    log.info("beats: %.1fs, bpm=%.2f, %d beats", timings["beats"], beats.bpm, len(beats.beats))

    # 4. 8-count validation
    log.info("=== 8-count validation ===")
    # Extract onsets from the "other" stem (which has requinto + segunda)
    req_onsets = [o.time_sec for o in detect_onsets(sep.stems.get("other", mix), sep.sr, min_strength=0.15)]
    bongo_onsets = [o.time_sec for o in detect_onsets(sep.stems.get("drums", mix), sep.sr, min_strength=0.10)]
    bar_idx, bar_conf, phase_offset = validate_8count(
        beats.beats, beats.bpm, req_onsets=req_onsets, bongo_onsets=bongo_onsets
    )

    # 5. Section detection
    log.info("=== Section detection ===")
    t = time.time()
    sections = detect_sections(
        y_mix=mix,
        y_vocals=sep.stems.get("vocals"),
        y_drums=sep.stems.get("drums"),
        y_bass=sep.stems.get("bass"),
        sr=sep.sr,
        bpm=beats.bpm,
        duration_sec=duration,
        genre=genre,
    )
    timings["sections"] = time.time() - t
    log.info("sections: %.1fs, %d sections", timings["sections"], len(sections))

    # 6. Clave (salsa only)
    clave = None
    if genre == "salsa":
        log.info("=== Clave detection ===")
        t = time.time()
        clave = detect_clave(sep.stems.get("drums", mix), sep.stems.get("bass", mix), sep.sr, beats.bpm, duration)
        timings["clave"] = time.time() - t
        log.info("clave: %.1fs, %s conf=%.2f", timings["clave"], clave.direction, clave.confidence)

    # 6.5. Lyrics (optional, slow)
    lyrics_result = None
    if config.transcribe and "vocals" in sep.stems:
        log.info("=== Lyrics (Whisper) ===")
        t = time.time()
        try:
            from compas_ml.lyrics import transcribe

            lyrics_result = transcribe(
                sep.stems["vocals"],
                sep.sr,
                model_name=config.whisper_model,
                device=config.whisper_device,
            )
            timings["lyrics"] = time.time() - t
            log.info("lyrics: %.1fs, %d lines, %s", timings["lyrics"], len(lyrics_result.lines), lyrics_result.language)
        except Exception as e:
            log.warning("Lyrics transcription failed: %s", e)
            timings["lyrics"] = time.time() - t

    # 7. Musicality curves
    log.info("=== Musicality ===")
    t = time.time()
    n_bars = max(1, int(duration / (60.0 / beats.bpm * 8))) if beats.bpm > 0 else 32
    musicality = {
        "energy": compute_rms_curve(mix, n_bars),
        "onset_density": compute_rms_curve(sep.stems.get("drums", mix), n_bars),
        "spectral_flux": _spectral_flux_curve(mix, sep.sr, n_bars),
        "bass_rms": compute_rms_curve(sep.stems.get("bass", mix), n_bars),
        "vocal_activity": compute_rms_curve(sep.stems.get("vocals", mix), n_bars),
        "percussion_density": compute_rms_curve(sep.stems.get("drums", mix), n_bars),
        "hits": _collect_hits(beats, sections),
    }
    if genre == "salsa":
        # Salsa extras
        musicality["piano_montuno_density"] = compute_rms_curve(sep.stems.get("other", mix), n_bars)
        musicality["clave_direction"] = [clave.direction if clave else "unclear"] * n_bars
    timings["musicality"] = time.time() - t
    log.info("musicality: %.1fs, %d curves", timings["musicality"], len(musicality))

    # 8. Build gems from stem onsets
    log.info("=== Gems ===")
    gems = _build_gems(sep, mix, sr, duration)

    # 9. Validation / metadata
    total_elapsed = time.time() - t_start
    log.info("=== Pipeline done in %.1fs ===", total_elapsed)

    # 10. Build the final analysis dict
    song_id = safe_filename(source_path.stem)
    analysis = {
        "$schema": "https://compas.dev/schemas/analysis-v1.json",
        "song_id": song_id,
        "version": 1,
        "model_set": {
            "separator": config.separator,
            "beats": beats.method,
            "sections": config.section_method,
        },
        "status": "done",
        "confidence_overall": _overall_confidence(beats, sections, sep, bar_conf, clave),
        "metadata": {
            "title": source_path.stem,
            "artist": "Unknown",
            "album": None,
            "year": None,
            "genre": genre,
            "subgenre": None,
            "language": None,
        },
        "global": {
            "bpm": beats.bpm,
            "bpm_confidence": _conf_to_label(beats.bpm_confidence),
            "bpm_alt": beats.bpm_alt,
            "bpm_notes": "",
            "key": None,
            "time_signature": "4/4",
            "first_downbeat_sec": beats.first_downbeat_sec,
            "first_8count_start_sec": beats.first_8count_start_sec + phase_offset,
            "feel": beats.feel,
            "clave_direction": clave.direction if clave else None,
            "clave_notes": "",
        },
        "downbeats": beats.downbeats,
        "beats": beats.beats,
        "sections": [
            {
                "start_sec": s.start_sec,
                "end_sec": s.end_sec,
                "type": s.type,
                "confidence": _conf_to_label(s.confidence),
                "notes": s.notes,
            }
            for s in sections
        ],
        "stems_present": _stems_present(sep),
        "stems_quality": {k: {"sdr_db_estimate": v, "bleed": _bleed_label(v), "notes": ""} for k, v in sep.sdr_estimates.items()},
        "lyrics": (
            {
                "language": lyrics_result.language,
                "segments": [
                    {
                        "start_sec": ln.start_sec,
                        "end_sec": ln.end_sec,
                        "text": ln.text,
                        "translation": None,
                        "phonetic_ipa": None,
                        "vocal_type": ln.vocal_type,
                    }
                    for ln in lyrics_result.lines
                ],
            }
            if lyrics_result
            else {"language": "unknown", "segments": []}
        ),
        "clave_segments": (
            [
                {
                    "start_sec": 0.0,
                    "end_sec": duration,
                    "direction": clave.direction,
                    "confidence": _conf_to_label(clave.confidence),
                    "notes": "",
                }
            ]
            + [
                {
                    "start_sec": sw["start_sec"],
                    "end_sec": sw["start_sec"] + 16 * 60.0 / beats.bpm,
                    "direction": sw["to"],
                    "confidence": "med",
                    "notes": f"switched from {sw['from']}",
                }
                for sw in (clave.switches if clave else [])
            ]
            if clave
            else []
        ),
        "musicality": musicality,
        "gems": gems,  # for the grid
        "timings_sec": timings,
        "elapsed_sec": total_elapsed,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Write to disk
    (out_dir / "analysis.json").write_text(json.dumps(analysis, indent=2, default=_json_default))
    log.info("Wrote analysis to %s", out_dir / "analysis.json")

    return analysis


def _spectral_flux_curve(y: np.ndarray, sr: int, n_bars: int) -> list[float]:
    """Spectral flux per bar — quick measure of how 'new' each bar sounds."""
    import librosa

    if y.size == 0:
        return [0.0] * n_bars
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=512))
    diff = np.diff(S, axis=1)
    diff = np.maximum(0, diff).sum(axis=0)
    bar_len = len(diff) // n_bars
    out = []
    for i in range(n_bars):
        s = i * bar_len
        e = (i + 1) * bar_len
        out.append(float(diff[s:e].mean()) if e > s else 0.0)
    if out and max(out) > 0:
        out = [v / max(out) for v in out]
    return out


def _collect_hits(beats, sections) -> list[dict]:
    """Synthesize hit events: downbeats + section boundaries."""
    hits = []
    for t in beats.downbeats:
        hits.append({"time_sec": t, "strength": 0.9, "type": "downbeat", "notes": ""})
    for s in sections:
        hits.append({"time_sec": s.start_sec, "strength": 0.7, "type": "accent", "notes": s.type})
    return sorted(hits, key=lambda h: h["time_sec"])


def _build_gems(sep, mix, sr, duration) -> list[dict]:
    """Extract per-stem onset gems for the grid."""
    gems: list[dict] = []
    stem_to_compas = {
        "vocals": "vocals_lead",
        "drums": "bongo",
        "bass": "bass",
        "other": "requinto",
    }
    for demucs_name, compas_name in stem_to_compas.items():
        if demucs_name not in sep.stems:
            continue
        onsets = detect_onsets(sep.stems[demucs_name], sep.sr, min_strength=0.10)
        for o in onsets:
            gems.append(
                {
                    "time_sec": o.time_sec,
                    "stem": compas_name,
                    "pitch_midi": o.pitch_midi,
                    "strength": o.strength,
                    "is_hit": o.is_hit,
                }
            )
    gems.sort(key=lambda g: g["time_sec"])
    return gems


def _stems_present(sep) -> dict[str, bool]:
    """Map our canonical 18-stem taxonomy to what Demucs actually produced."""
    # Demucs only gives 4 stems. Mark only the 4 we have.
    has = {k: False for k in [
        "vocals_lead", "vocals_back", "requinto", "segunda", "bass", "bongo",
        "guira", "tambora", "clave", "palmas", "synth", "horns", "piano",
        "congas", "timbales", "cowbell", "maracas", "guiro",
    ]}
    if "vocals" in sep.stems:
        has["vocals_lead"] = True
        has["vocals_back"] = True
    if "drums" in sep.stems:
        has["bongo"] = True
        has["timbales"] = True
        has["cowbell"] = True
        has["congas"] = True
    if "bass" in sep.stems:
        has["bass"] = True
    if "other" in sep.stems:
        has["requinto"] = True
        has["segunda"] = True
        has["piano"] = True
        has["synth"] = True
    return has


def _overall_confidence(beats, sections, sep, bar_conf, clave) -> float:
    score = 0.0
    score += beats.bpm_confidence * 0.3
    if sections:
        score += (sum(s.confidence for s in sections) / len(sections)) * 0.3
    score += (bar_conf or 0.5) * 0.2
    if sep.sdr_estimates:
        avg_sdr = sum(max(0, v) for v in sep.sdr_estimates.values()) / len(sep.sdr_estimates)
        score += min(1.0, avg_sdr / 15.0) * 0.1
    if clave:
        score += clave.confidence * 0.1
    return min(1.0, score)


def _conf_to_label(c: float) -> str:
    if c >= 0.7:
        return "high"
    if c >= 0.4:
        return "med"
    return "low"


def _bleed_label(sdr: float) -> str:
    if sdr >= 8:
        return "low"
    if sdr >= 4:
        return "med"
    return "high"


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)
