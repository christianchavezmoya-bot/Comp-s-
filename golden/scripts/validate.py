#!/usr/bin/env python3
"""Validate a golden set annotation JSON against the schema and basic sanity rules.

Usage:
    python golden/scripts/validate.py golden/songs/<uuid>.json
    python golden/scripts/validate.py golden/songs/  # all of them
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACHATA_SECTIONS = {
    "intro", "verso", "pre_coro", "coro", "mambo", "majae",
    "soneo", "puente", "breakdown", "outro",
}
SALSA_SECTIONS = {
    "intro", "verso", "coro_pregon", "coro", "montuno",
    "mambo_sub", "diablo_sub", "mona_sub", "especial_sub", "soneo", "coda",
}
REQUIRED_TOP_KEYS = {
    "$schema", "song_id", "intake", "metadata", "global",
    "downbeats", "beats", "sections", "stems_present",
    "lyrics", "hits",
}
REQUIRED_INTAKE = {"annotator_id", "annotated_at", "duration_sec"}
REQUIRED_GLOBAL = {"bpm", "bpm_confidence", "time_signature", "first_downbeat_sec", "first_8count_start_sec", "feel"}


def validate_one(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path.name}: invalid JSON: {e}"]

    missing = REQUIRED_TOP_KEYS - set(data.keys())
    if missing:
        errors.append(f"{path.name}: missing top-level keys: {sorted(missing)}")

    # intake
    intake = data.get("intake", {})
    miss_i = REQUIRED_INTAKE - set(intake.keys())
    if miss_i:
        errors.append(f"{path.name}: intake missing: {sorted(miss_i)}")

    # global
    g = data.get("global", {})
    miss_g = REQUIRED_GLOBAL - set(g.keys())
    if miss_g:
        errors.append(f"{path.name}: global missing: {sorted(miss_g)}")
    if g.get("bpm", 0) <= 0:
        errors.append(f"{path.name}: global.bpm must be > 0")
    if g.get("bpm_confidence") not in ("high", "med", "low"):
        errors.append(f"{path.name}: global.bpm_confidence must be high/med/low")
    if g.get("feel") not in ("single_time", "double_time", "half_time"):
        errors.append(f"{path.name}: global.feel must be single_time/double_time/half_time")

    # sections
    sections = data.get("sections", [])
    if not sections:
        errors.append(f"{path.name}: sections must be non-empty")
    last_end = 0.0
    for i, sec in enumerate(sections):
        for k in ("start_sec", "end_sec", "type", "confidence"):
            if k not in sec:
                errors.append(f"{path.name}: section[{i}] missing {k}")
        if sec.get("start_sec", -1) < 0:
            errors.append(f"{path.name}: section[{i}] start_sec < 0")
        if sec.get("end_sec", -1) <= sec.get("start_sec", 0):
            errors.append(f"{path.name}: section[{i}] end_sec <= start_sec")
        if sec.get("start_sec", 0) < last_end - 0.01:
            errors.append(f"{path.name}: section[{i}] overlaps previous (start {sec.get('start_sec')} < last_end {last_end})")
        last_end = sec.get("end_sec", last_end)
        # type taxonomy
        genre = data.get("metadata", {}).get("genre")
        valid = BACHATA_SECTIONS if genre == "bachata" else SALSA_SECTIONS if genre == "salsa" else (BACHATA_SECTIONS | SALSA_SECTIONS)
        if sec.get("type") not in valid:
            errors.append(f"{path.name}: section[{i}].type={sec.get('type')!r} not in {genre} taxonomy")
        if sec.get("confidence") not in ("high", "med", "low"):
            errors.append(f"{path.name}: section[{i}].confidence must be high/med/low")

    # first section should start at 0
    if sections and abs(sections[0].get("start_sec", -1)) > 0.01:
        errors.append(f"{path.name}: first section must start at 0 (got {sections[0].get('start_sec')})")

    # last section should end at duration (±0.5s)
    if sections:
        last = sections[-1]
        intake_dur = intake.get("duration_sec", 0)
        if intake_dur > 0 and abs(last.get("end_sec", 0) - intake_dur) > 0.5:
            errors.append(f"{path.name}: last section end_sec ({last.get('end_sec')}) != duration ({intake_dur})")

    # downbeats: monotonic, sorted
    downs = data.get("downbeats", [])
    if downs and downs != sorted(downs):
        errors.append(f"{path.name}: downbeats must be sorted ascending")

    # lyrics
    lyrics = data.get("lyrics", {})
    if lyrics and "language" in lyrics and "segments" in lyrics:
        last_end_lyr = 0.0
        for i, seg in enumerate(lyrics.get("segments", [])):
            if seg.get("start_sec", -1) < last_end_lyr - 0.01:
                errors.append(f"{path.name}: lyrics[{i}] overlaps previous")
            last_end_lyr = seg.get("end_sec", last_end_lyr)
            if seg.get("vocal_type") not in ("lead", "backing", "coro", "soneo", "ad_lib", "spoken"):
                errors.append(f"{path.name}: lyrics[{i}].vocal_type invalid")

    # clave for salsa
    if data.get("metadata", {}).get("genre") == "salsa":
        if not data.get("clave_segments"):
            errors.append(f"{path.name}: salsa song must have clave_segments")
        for i, cs in enumerate(data.get("clave_segments", [])):
            if cs.get("direction") not in ("son_2_3", "son_3_2", "rumba_2_3", "rumba_3_2", "none", "unclear"):
                errors.append(f"{path.name}: clave_segments[{i}].direction invalid")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="JSON file or directory")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.path.is_dir():
        files = sorted(args.path.glob("*.json"))
    else:
        files = [args.path]

    total_errors = 0
    for f in files:
        errs = validate_one(f)
        if errs:
            total_errors += len(errs)
            for e in errs:
                print(f"  ❌ {e}")
        else:
            if not args.quiet:
                print(f"  ✅ {f.name}")

    if total_errors > 0:
        print(f"\n{total_errors} error(s) across {len(files)} file(s)")
        return 1
    else:
        print(f"\nAll {len(files)} file(s) valid ✅")
        return 0


if __name__ == "__main__":
    sys.exit(main())
