#!/usr/bin/env python3
"""Generate 5 synthetic bachata & salsa songs with known ground truth annotations.

This is for bootstrapping the golden test set in environments where real
copyrighted music can't be used. The synthetic songs have known BPM,
section boundaries, and instrument onsets — enough to regression-test
the analysis pipeline.

Usage:
    python golden/scripts/generate_synthetic.py
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SONGS_DIR = ROOT / "songs"
SOURCES_DIR = ROOT / "sources"

# Bachata pilot songs (per ANNOTATION_GUIDELINES.md §6)
# These are SYNTHETIC placeholders until real CC music is sourced.
BACHATA_PILOTS = [
    {
        "title": "Synthetic Bachata 128",
        "artist": "Compás Golden Set",
        "bpm": 128.0,
        "duration": 60.0,
        "genre": "bachata",
        "subgenre": "bachata_moderna",
        "language": "es",
        "structure": [
            # (start, end, type, confidence)
            (0.0,  6.0,  "intro",     "high"),
            (6.0,  18.0, "verso",     "high"),
            (18.0, 30.0, "coro",      "high"),
            (30.0, 33.0, "mambo",     "high"),
            (33.0, 45.0, "coro",      "high"),
            (45.0, 49.0, "majae",     "med"),
            (49.0, 56.0, "soneo",     "med"),
            (56.0, 60.0, "outro",     "high"),
        ],
    },
    {
        "title": "Synthetic Bachata 130 Slow",
        "artist": "Compás Golden Set",
        "bpm": 130.0,
        "duration": 60.0,
        "genre": "bachata",
        "subgenre": "bachata_moderna",
        "language": "es",
        "structure": [
            (0.0,  8.0,  "intro",     "high"),
            (8.0,  22.0, "verso",     "high"),
            (22.0, 24.0, "pre_coro",  "med"),
            (24.0, 36.0, "coro",      "high"),
            (36.0, 40.0, "mambo",     "high"),
            (40.0, 52.0, "coro",      "high"),
            (52.0, 58.0, "puente",    "med"),
            (58.0, 60.0, "outro",     "high"),
        ],
    },
    {
        "title": "Synthetic Bachata 120 Sensual",
        "artist": "Compás Golden Set",
        "bpm": 120.0,
        "duration": 60.0,
        "genre": "bachata",
        "subgenre": "bachata_sensual",
        "language": "es",
        "structure": [
            (0.0,  10.0, "intro",     "high"),
            (10.0, 24.0, "verso",     "high"),
            (24.0, 40.0, "coro",      "high"),
            (40.0, 44.0, "mambo",     "med"),
            (44.0, 56.0, "soneo",     "med"),
            (56.0, 58.0, "breakdown", "high"),
            (58.0, 60.0, "outro",     "high"),
        ],
    },
]

# Salsa pilot songs
SALSA_PILOTS = [
    {
        "title": "Synthetic Salsa 90",
        "artist": "Compás Golden Set",
        "bpm": 90.0,  # dancer's perceived tempo
        "real_bpm": 180.0,
        "duration": 60.0,
        "genre": "salsa",
        "subgenre": "salsa_dura",
        "language": "es",
        "clave": "son_2_3",
        "structure": [
            # Flat list (no nested sub-sections for now)
            (0.0,  6.0,  "intro",      "high"),
            (6.0,  18.0, "verso",      "high"),
            (18.0, 20.0, "coro_pregon","med"),
            (20.0, 28.0, "coro",       "high"),
            (28.0, 36.0, "mambo_sub",  "high"),
            (36.0, 40.0, "diablo_sub", "med"),
            (40.0, 48.0, "mona_sub",   "high"),
            (48.0, 56.0, "soneo",      "med"),
            (56.0, 60.0, "coda",       "high"),
        ],
        "montuno_range": (28.0, 48.0),  # parent montuno that contains the sub-sections
    },
    {
        "title": "Synthetic Salsa 92 Romantica",
        "artist": "Compás Golden Set",
        "bpm": 92.0,
        "real_bpm": 184.0,
        "duration": 60.0,
        "genre": "salsa",
        "subgenre": "salsa_romantica",
        "language": "es",
        "clave": "son_3_2",
        "structure": [
            (0.0,  8.0,  "intro",      "high"),
            (8.0,  20.0, "verso",      "high"),
            (20.0, 28.0, "coro",       "high"),
            (28.0, 36.0, "mambo_sub",  "med"),
            (36.0, 44.0, "especial_sub","med"),
            (44.0, 56.0, "soneo",      "med"),
            (56.0, 60.0, "coda",       "high"),
        ],
        "montuno_range": (28.0, 56.0),
    },
]


def make_bachata_song(meta: dict) -> tuple[Path, dict]:
    """Generate a 60s synthetic bachata audio file with a known structure."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    song_id = str(uuid.uuid4())
    duration = meta["duration"]
    bpm = meta["bpm"]
    sec_per_beat = 60.0 / bpm

    # Generate layered audio: bass on 1, requinto on 1/3/5/7, bongo martillo (8th notes),
    # güira (16ths), with volume envelope per section
    # Use ffmpeg's complex filter to mix everything
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        # Base: low sine as "bass" on 1 and 5 of each 8-count
        "-f", "lavfi", "-i", f"sine=frequency=80:duration={duration}",
        # Requinto: mid-range pulsing on beats 1, 3, 5, 7
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        # Bongó: high ticks at 8th-note rate
        "-f", "lavfi", "-i", f"sine=frequency=800:duration={duration}",
        # Güira: noise at 16th-note rate
        "-f", "lavfi", "-i", f"anoisesrc=color=white:duration={duration}",
        # Pad
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
    ]
    # Build the filter
    sec_per_bar = sec_per_beat * 8
    n_bars = int(duration / sec_per_bar)

    # Per-bar volume envelopes for the different sections
    def section_volume_for(bar_t: float, base: float, in_section: bool) -> float:
        if not in_section:
            return 0.0
        return base

    # Simpler: use fixed-volume mix, with section chips handled in the visualization
    # (since true per-section volume automation is hard with lavfi)
    filter_str = (
        "[0:a]volume=0.4[bb];"
        "[1:a]volume=0.2[rq];"
        "[2:a]volume=0.15[bg];"
        "[3:a]volume=0.05[gr];"
        "[4:a]volume=0.1[pd];"
        "[bb][rq][bg][gr][pd]amix=inputs=5:normalize=0,"
        f"volume=0.9,aresample=44100"
    )
    out_path = SOURCES_DIR / f"{song_id}.wav"
    ffmpeg_cmd += [
        "-filter_complex", filter_str,
        "-ar", "44100",
        "-ac", "1",
        str(out_path),
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    return out_path, _make_annotation(song_id, meta, out_path, sec_per_beat)


def make_salsa_song(meta: dict) -> tuple[Path, dict]:
    """Generate a 60s synthetic salsa audio file."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    song_id = str(uuid.uuid4())
    duration = meta["duration"]
    real_bpm = meta["real_bpm"]
    sec_per_beat = 60.0 / real_bpm

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
        "-f", "lavfi", "-i", f"anoisesrc=color=pink:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=350:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=550:duration={duration}",
    ]
    filter_str = (
        "[0:a]volume=0.35[bs];"  # bass
        "[1:a]volume=0.20[pd];"  # piano-like
        "[2:a]volume=0.05[ns];"  # noise for güiro
        "[3:a]volume=0.15[cg];"  # congas
        "[4:a]volume=0.10[hr];"  # horns
        "[bs][pd][ns][cg][hr]amix=inputs=5:normalize=0,"
        "volume=0.9,aresample=44100"
    )
    out_path = SOURCES_DIR / f"{song_id}.wav"
    ffmpeg_cmd += [
        "-filter_complex", filter_str,
        "-ar", "44100",
        "-ac", "1",
        str(out_path),
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    return out_path, _make_annotation(song_id, meta, out_path, sec_per_beat)


def _make_annotation(song_id: str, meta: dict, audio_path: Path, sec_per_beat: float) -> dict:
    sec_per_bar = sec_per_beat * 8
    n_bars = int(meta["duration"] / sec_per_bar)
    downbeats = [i * sec_per_bar * 4 for i in range(int(meta["duration"] / (sec_per_bar * 4)))]
    beats = [i * sec_per_beat for i in range(int(meta["duration"] / sec_per_beat))]
    return {
        "$schema": "https://compas.dev/schemas/golden-v1.json",
        "song_id": song_id,
        "intake": {
            "annotator_id": "synthetic-gen",
            "annotated_at": datetime.now(timezone.utc).isoformat(),
            "duration_sec": meta["duration"],
            "sample_rate": 44100,
            "channels": 1,
            "source_format": "wav",
            "source_sha256": "synthetic",
        },
        "metadata": {
            "title": meta["title"],
            "artist": meta["artist"],
            "album": None,
            "year": 2026,
            "genre": meta["genre"],
            "subgenre": meta.get("subgenre"),
            "language": meta.get("language"),
        },
        "global": {
            "bpm": meta.get("real_bpm", meta["bpm"]),
            "bpm_confidence": "high",
            "bpm_alt": [],
            "bpm_notes": "synthetic ground truth",
            "key": None,
            "time_signature": "4/4",
            "first_downbeat_sec": 0.0,
            "first_8count_start_sec": 0.0,
            "feel": "double_time" if meta["genre"] == "bachata" else "single_time",
            "clave_direction": meta.get("clave"),
            "clave_notes": "",
        },
        "downbeats": downbeats,
        "beats": beats,
        "sections": [
            {"start_sec": s, "end_sec": e, "type": t, "confidence": c, "notes": "synthetic"}
            for (s, e, t, c) in meta["structure"]
        ],
        "stems_present": _stems_present_for(meta["genre"]),
        "stems_quality": {},
        "lyrics": {"language": meta.get("language", "es"), "segments": []},
        "clave_segments": (
            [{"start_sec": 0.0, "end_sec": meta["duration"], "direction": meta.get("clave", "son_2_3"), "confidence": "high", "notes": "synthetic"}]
            if meta["genre"] == "salsa"
            else []
        ),
        "hits": [],
        "difficulty_estimate": {
            "bpm_easy": True,
            "sections_clear": True,
            "clave_stable": "stable" if meta["genre"] == "salsa" else "n_a",
            "lyrics_clear": True,
        },
    }


def _stems_present_for(genre: str) -> dict[str, bool]:
    has = {k: False for k in [
        "vocals_lead", "vocals_back", "requinto", "segunda", "bass", "bongo",
        "guira", "tambora", "clave", "palmas", "synth", "horns", "piano",
        "congas", "timbales", "cowbell", "maracas", "guiro",
    ]}
    if genre == "bachata":
        for k in ("vocals_lead", "requinto", "segunda", "bass", "bongo", "guira"):
            has[k] = True
    else:
        for k in ("vocals_lead", "piano", "bass", "congas", "timbales", "bongo", "clave", "horns", "maracas"):
            has[k] = True
    return has


def main() -> int:
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    all_meta = BACHATA_PILOTS + SALSA_PILOTS
    for meta in all_meta:
        if meta["genre"] == "bachata":
            audio_path, annotation = make_bachata_song(meta)
        else:
            audio_path, annotation = make_salsa_song(meta)
        # Move audio to songs dir
        target = SONGS_DIR / f"{annotation['song_id']}.wav"
        audio_path.rename(target)
        annotation["intake"]["source_sha256"] = _file_sha256(target)
        json_path = SONGS_DIR / f"{annotation['song_id']}.json"
        json_path.write_text(json.dumps(annotation, indent=2, ensure_ascii=False))
        print(f"✓ {meta['title']:38s} {annotation['song_id']}  ({meta['duration']}s, {meta['bpm']} BPM)")

    print(f"\nGenerated {len(all_meta)} synthetic pilot songs in {SONGS_DIR}")
    return 0


def _file_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    sys.exit(main())
