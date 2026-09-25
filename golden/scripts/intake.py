#!/usr/bin/env python3
"""Intake a new audio file into the golden set.

Usage:
    python golden/scripts/intake.py path/to/song.flac

Generates:
    golden/songs/<uuid>.flac  (copy of the source)
    golden/songs/<uuid>.json  (annotation skeleton with song_id pre-filled)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SONGS_DIR = ROOT / "songs"
SCHEMA = "https://compas.dev/schemas/golden-v1.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0:
            info = json.loads(out.stdout)
            return float(info.get("format", {}).get("duration", 0.0))
    except Exception:
        pass
    return 0.0


def ffprobe_samplerate(path: Path) -> int:
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0:
            info = json.loads(out.stdout)
            streams = info.get("streams", [])
            if streams:
                return int(streams[0].get("sample_rate", 44100))
    except Exception:
        pass
    return 44100


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path, help="Source audio file (FLAC preferred)")
    ap.add_argument("--annotator", default="user-001", help="Annotator ID")
    ap.add_argument(
        "--genre",
        choices=["bachata", "salsa"],
        default="bachata",
        help="Genre (required for analysis; can be edited in JSON)",
    )
    args = ap.parse_args()

    src = args.source.resolve()
    if not src.exists():
        print(f"ERROR: source not found: {src}", file=sys.stderr)
        return 1

    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    song_id = str(uuid.uuid4())
    ext = src.suffix or ".flac"
    dst = SONGS_DIR / f"{song_id}{ext}"
    shutil.copy2(src, dst)
    sha = sha256_of(dst)
    duration = ffprobe_duration(dst)
    sr = ffprobe_samplerate(dst)

    now = datetime.now(timezone.utc).isoformat()
    skeleton = {
        "$schema": SCHEMA,
        "song_id": song_id,
        "intake": {
            "annotator_id": args.annotator,
            "annotated_at": now,
            "duration_sec": duration,
            "sample_rate": sr,
            "channels": 2,
            "source_format": ext.lstrip("."),
            "source_sha256": sha,
        },
        "metadata": {
            "title": src.stem,
            "artist": "Unknown",
            "album": None,
            "year": None,
            "genre": args.genre,
            "subgenre": None,
            "language": None,
        },
        "global": {
            "bpm": 0.0,
            "bpm_confidence": "low",
            "bpm_alt": [],
            "bpm_notes": "",
            "key": None,
            "time_signature": "4/4",
            "first_downbeat_sec": 0.0,
            "first_8count_start_sec": 0.0,
            "feel": "double_time" if args.genre == "bachata" else "single_time",
            "clave_direction": None,
            "clave_notes": "",
        },
        "downbeats": [],
        "beats": [],
        "sections": [],
        "stems_present": {k: False for k in [
            "vocals_lead", "vocals_back", "requinto", "segunda", "bass", "bongo",
            "guira", "tambora", "clave", "palmas", "synth", "horns", "piano",
            "congas", "timbales", "cowbell", "maracas", "guiro",
        ]},
        "stems_quality": {},
        "lyrics": {"language": "es", "segments": []},
        "clave_segments": [],
        "hits": [],
        "difficulty_estimate": {
            "bpm_easy": False,
            "sections_clear": False,
            "clave_stable": "n_a",
            "lyrics_clear": False,
        },
    }

    json_path = SONGS_DIR / f"{song_id}.json"
    json_path.write_text(json.dumps(skeleton, indent=2, ensure_ascii=False))

    print(f"Intake complete.")
    print(f"  song_id:  {song_id}")
    print(f"  audio:    {dst}")
    print(f"  json:     {json_path}")
    print(f"  duration: {duration:.2f}s @ {sr} Hz")
    print(f"  sha256:   {sha}")
    print()
    print(f"Next: open {json_path.name} and start annotating.")
    print(f"See ANNOTATION_GUIDELINES.md for the schema and workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
