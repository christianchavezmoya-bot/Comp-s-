#!/usr/bin/env python3
"""Report golden set coverage: genre, style, BPM range, language, annotator.

Usage:
    python golden/scripts/stats.py [golden/songs/]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", type=Path, default=Path("golden/songs"))
    args = ap.parse_args()

    if not args.path.is_dir():
        print(f"ERROR: not a directory: {args.path}", file=sys.stderr)
        return 1

    files = sorted(args.path.glob("*.json"))
    if not files:
        print(f"No JSON files found in {args.path}")
        return 0

    by_genre: Counter = Counter()
    by_style: Counter = Counter()
    by_lang: Counter = Counter()
    by_annotator: Counter = Counter()
    bpms_bachata: list[float] = []
    bpms_salsa: list[float] = []
    section_counts: Counter = Counter()

    for f in files:
        try:
            d = json.loads(f.read_text())
        except Exception as e:
            print(f"  ⚠️  {f.name}: failed to parse: {e}")
            continue

        meta = d.get("metadata", {})
        by_genre[meta.get("genre", "?")] += 1
        by_style[meta.get("subgenre") or "—"] += 1
        by_lang[meta.get("language") or "—"] += 1
        by_annotator[d.get("intake", {}).get("annotator_id", "?")] += 1
        bpm = d.get("global", {}).get("bpm", 0)
        if meta.get("genre") == "bachata":
            bpms_bachata.append(bpm)
        elif meta.get("genre") == "salsa":
            bpms_salsa.append(bpm)
        for sec in d.get("sections", []):
            section_counts[sec.get("type", "?")] += 1

    print(f"=== Golden set coverage ===")
    print(f"Total songs: {len(files)}")
    print()
    print(f"By genre:")
    for g, n in by_genre.most_common():
        print(f"  {g:10s} {n:3d}")
    print()
    print(f"By style/subgenre:")
    for s, n in by_style.most_common():
        print(f"  {s:30s} {n:3d}")
    print()
    print(f"By language:")
    for l, n in by_lang.most_common():
        print(f"  {l:6s} {n:3d}")
    print()
    print(f"By annotator:")
    for a, n in by_annotator.most_common():
        print(f"  {a:20s} {n:3d}")
    print()
    if bpms_bachata:
        print(f"Bachata BPM: min={min(bpms_bachata):.0f} max={max(bpms_bachata):.0f} mean={sum(bpms_bachata)/len(bpms_bachata):.1f}")
    if bpms_salsa:
        print(f"Salsa   BPM: min={min(bpms_salsa):.0f} max={max(bpms_salsa):.0f} mean={sum(bpms_salsa)/len(bpms_salsa):.1f}")
    print()
    print(f"Section types observed:")
    for s, n in section_counts.most_common():
        print(f"  {s:20s} {n:3d}")

    # Coverage goals
    print()
    print(f"=== Coverage goals (per ANNOTATION_GUIDELINES.md §1) ===")
    target_bachata = 100
    target_salsa = 100
    print(f"  Bachata: {by_genre.get('bachata', 0)}/{target_bachata} ({(by_genre.get('bachata', 0)/target_bachata*100):.0f}%)")
    print(f"  Salsa:   {by_genre.get('salsa', 0)}/{target_salsa} ({(by_genre.get('salsa', 0)/target_salsa*100):.0f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
