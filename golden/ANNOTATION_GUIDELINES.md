# Compás — Golden Test Set Annotation Guidelines

> The golden test set is the **single most important artifact** in the project. It is the source of truth for what "correct" looks like, and the yardstick every ML model upgrade must beat. This document tells you exactly what to annotate, how, and with which tools.

---

## 0. Why we annotate by hand

A "ground truth" file for a song answers questions like:
- Is this bachata 128 BPM or 130?
- Where does the coro start?
- Is this a mambo section or a majae?
- Is this salsa 2-3 clave or 3-2?

If we don't have ground truth, we can't measure whether the model is right. The only way to get ground truth is a human (or two humans + an adjudicator) listening carefully and writing down the answers. **No model can validate itself.**

The 200-song golden set feeds:
1. **CI regression tests** — every model upgrade must hit ≥ X% accuracy
2. **Per-section accuracy reports** — "we get 95% on Intro detection but only 70% on Mambo"
3. **Per-instrument SDR measurement** — stem separation quality
4. **Per-genre model selection** — different hyperparameters for bachata vs salsa
5. **Confusion matrices** — "model confuses Majae with Soneo 22% of the time"
6. **Demo songs** — the first 5 songs are the "launch demo", polished and verified

---

## 1. Scope and sample composition

### 1.1 Total: 200 songs

| Genre | Count | Why this split |
|---|---|---|
| **Bachata** | 100 | Most requested genre; canonical example (Dentro only supports this) |
| **Salsa** | 100 | Clave + montuno complexity demands more sample mass |

### 1.2 Style coverage per genre (10 styles × 10 songs = 100)

#### Bachata styles
1. Bachata Dominicana (traditional, bolero-style with bongó)
2. Bachata Moderna (post-1990s, Juan Luis Guerra, Aventura)
3. Bachata Urbana (urban remix, Aventura-style, Romeo Santos)
4. Bachata Sensual (slow, body movement focused, 105–125 BPM)
5. Bachata Fusion (with reggaeton, dembow, pop)
6. Bachatango (with tango influences)
7. Bachata Romántica (slow, vocal-forward)
8. Merengue-based Bachata (tambora instead of bongó)
9. Bachata con Guitarra Clásica (acoustic, nylon-string only)
10. Bachata Acústica (live-recorded, no synths)

#### Salsa styles
1. Salsa Cubana / Casino (Cuban-style, contratiempo)
2. Salsa Lineal / LA-style (on1, Eddie Torres school)
3. Salsa On2 / NY-style (mambo on 2, Eddie Torres / Razz M'Tazz)
4. Salsa Dura (hard, Fania-style, 1970s)
5. Salsa Romántica (1990s, vocal-forward, romantic)
6. Timba (Cuban, complex, post-1990s)
7. Salsa con Son (traditional son-salsa)
8. Charanga (violin/flute front)
9. Salsa Urbana (with reggaeton influence)
10. Salsa Instrumental (no vocals, all instrumental break / mambo sections)

### 1.3 BPM coverage per genre
- **Bachata**: 5 songs at 100–115, 60 at 115–140, 25 at 140–155, 10 at 155+ (the rare fast ones)
- **Salsa**: 30 at 160–180 (slow salsa), 60 at 180–200 (typical), 10 at 200+ (timba / fast)

### 1.4 Vocal-language coverage
- Spanish: 60% (Latin America)
- English: 20%
- Spanglish: 15%
- Other (Portuguese, Italian): 5%

### 1.5 Where to get the songs
Public domain / Creative Commons preferred. Sources:
- Free Music Archive (FMA) — has some bachata / salsa with permissive licenses
- ccMixter
- Internet Archive
- YouTube Audio Library
- Bands who explicitly release under CC
- Self-recorded or community-contributed (with explicit permission)

**DO NOT** include commercial tracks in the golden set. They're not redistributable, and we'd risk a takedown. The library of *commercial* tracks is for the user-upload library, not the golden set.

---

## 2. What you annotate (the schema)

Every song gets **one JSON file** with this exact structure. Filename = `{song_id}.json` where `song_id` is a stable UUID we generate at intake.

```json
{
  "$schema": "https://compas.dev/schemas/golden-v1.json",
  "song_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "intake": {
    "annotator_id": "user-001",
    "annotated_at": "2026-09-25T10:00:00Z",
    "duration_sec": 234.5,
    "sample_rate": 44100,
    "channels": 2,
    "source_format": "flac",
    "source_sha256": "abc123..."
  },
  "metadata": {
    "title": "Obsesión",
    "artist": "Aventura",
    "album": "We Broke the Rules",
    "year": 2004,
    "genre": "bachata",
    "subgenre": "bachata_moderna",
    "language": "es"
  },
  "global": {
    "bpm": 128.0,
    "bpm_confidence": "high",
    "bpm_notes": "Steady, no tempo changes",
    "key": "F minor",
    "time_signature": "4/4",
    "first_downbeat_sec": 0.0,
    "first_8count_start_sec": 0.0,
    "feel": "double_time",
    "clave_direction": null,
    "clave_notes": "N/A for bachata"
  },
  "downbeats": [0.0, 1.875, 3.75, 5.625, ...],
  "beats": [0.0, 0.469, 0.938, 1.406, ...],
  "sections": [
    { "start_sec": 0.0,   "end_sec": 8.0,   "type": "intro",      "confidence": "high", "notes": "" },
    { "start_sec": 8.0,   "end_sec": 24.0,  "type": "verso",      "confidence": "high", "notes": "" },
    { "start_sec": 24.0,  "end_sec": 40.0,  "type": "coro",       "confidence": "high", "notes": "" },
    { "start_sec": 40.0,  "end_sec": 44.0,  "type": "mambo",      "confidence": "high", "notes": "clear vocal break + bass fill" },
    { "start_sec": 44.0,  "end_sec": 60.0,  "type": "coro",       "confidence": "high", "notes": "" },
    { "start_sec": 60.0,  "end_sec": 92.0,  "type": "soneo",      "confidence": "high", "notes": "vocal improv over coro vamp" },
    { "start_sec": 92.0,  "end_sec": 100.0, "type": "puente",     "confidence": "med",  "notes": "key change to Ab major" },
    { "start_sec": 100.0, "end_sec": 103.0, "type": "breakdown",  "confidence": "high", "notes": "instrumentation drops, single hit" },
    { "start_sec": 103.0, "end_sec": 131.0, "type": "coro",       "confidence": "high", "notes": "final coro" },
    { "start_sec": 131.0, "end_sec": 140.0, "type": "outro",      "confidence": "high", "notes": "fade" }
  ],
  "stems_present": {
    "vocals_lead": true,
    "vocals_back": true,
    "requinto":   true,
    "segunda":    true,
    "bass":       true,
    "bongo":      true,
    "guira":      true,
    "tambora":    false,
    "clave":      false,
    "palmas":     false,
    "synth":      false,
    "horns":      false,
    "piano":      false,
    "congas":     false,
    "timbales":   false,
    "cowbell":    false,
    "maracas":    false,
    "guiro":      false
  },
  "stems_quality": {
    "vocals_lead": { "sdr_db_estimate": 12.0, "bleed": "low",  "notes": "" },
    "requinto":    { "sdr_db_estimate": 8.5,  "bleed": "med",  "notes": "some segunda bleed" }
  },
  "lyrics": {
    "language": "es",
    "segments": [
      { "start_sec": 8.0, "end_sec": 10.5, "text": "Son las cinco de la mañana", "vocal_type": "lead" },
      { "start_sec": 10.5, "end_sec": 12.5, "text": "y yo no he dormido nada", "vocal_type": "lead" },
      { "start_sec": 12.5, "end_sec": 14.0, "text": "oh-oh-oh", "vocal_type": "backing" }
    ]
  },
  "clave_segments": [
    { "start_sec": 0.0, "end_sec": 140.0, "direction": "n_a", "confidence": "high" }
  ],
  "hits": [
    { "time_sec": 0.0,  "strength": 0.95, "type": "downbeat",  "notes": "" },
    { "time_sec": 3.75, "strength": 0.80, "type": "downbeat",  "notes": "" }
  ],
  "difficulty_estimate": {
    "bpm_easy": true,
    "sections_clear": true,
    "clave_stable": "n_a",
    "lyrics_clear": true
  }
}
```

---

## 3. Field-by-field rules

### 3.1 `global.bpm`
- Listen to the song with a click track at your best guess.
- Use a tool like **Mixed In Key** or **BPM Tap** for a starting point.
- Adjust if you can clearly hear the song is at half-time or double-time.
- For bachata, **always report the "true" BPM** (where the kick lands on 1 and 5 of the 8-count), not the half-time feel.
- For salsa, report the **dancer's perceived tempo** (where they count 1) — typically half the "real" tempo of the song. Note this in `feel`.
- `confidence`: `high` if you're sure, `med` if ±2 BPM, `low` if you can't tell.

### 3.2 `global.first_downbeat_sec`
- The time of the very first beat 1 (or 2 for salsa on2).
- Often there's a count-in or silence before; the first downbeat is when the music "starts" in a dance sense.

### 3.3 `global.first_8count_start_sec`
- The time of the first beat of the first full 8-count bar.
- Usually the same as `first_downbeat_sec`, but if there's a 2-bar pickup, it could be a few seconds later.

### 3.4 `downbeats` and `beats`
- **Downbeats**: array of seconds, one per beat-1 (or beat-2 for on2 salsa). Continuous, no gaps.
- **Beats**: array of seconds, one per beat. Sparse is fine (every beat) but you can also list every 8th note if you want — both are acceptable. We prefer **downbeats only** for v1, with beats as optional.
- Compute these with a tool (see §4), then **manually correct** by listening. The tool's output is a starting point, not the answer.

### 3.5 `sections`
- An array of `[{start_sec, end_sec, type, confidence, notes}]`.
- The `type` MUST be one of the locked taxonomy (see §3.6).
- Sections must be **contiguous and non-overlapping**. The first section starts at 0, the last ends at `duration_sec`.
- If a section is ambiguous, mark `confidence: "low"` and explain in `notes`.
- `notes` is free text — "vocal break + bass fill, clear mambo moment" is great.

### 3.6 Section type taxonomy (closed list)

#### Bachata
- `intro`, `verso`, `pre_coro`, `coro`, `mambo`, `majae`, `soneo`, `puente`, `breakdown`, `outro`

#### Salsa
- `intro`, `verso`, `coro_pregon`, `coro`, `montuno`, `mambo_sub` (sub-section of montuno), `diablo_sub`, `mona_sub`, `especial_sub`, `soneo`, `coda`

If you encounter a section that doesn't fit (e.g. a "pre-intro", a "post-coro", a "cumbia breakdown"), use `notes` to describe it and use the closest type. We can extend the taxonomy after the golden set is done.

### 3.7 `stems_present` and `stems_quality`
- `stems_present` is a boolean for each known stem — is this instrument audible in the song?
- `stems_quality` is per-stem `sdr_db_estimate` (signal-to-distortion ratio in dB), `bleed` (low/med/high), and free-text `notes`.
- You don't have to measure SDR precisely — your best estimate after listening is fine.

### 3.8 `lyrics`
- `language`: ISO 639-1 code (`es`, `en`, `pt`, etc.).
- `segments`: an array of `[{start_sec, end_sec, text, vocal_type}]`.
- `vocal_type` is one of: `lead`, `backing`, `coro`, `soneo`, `ad_lib`, `spoken`.
- If a line is mixed (lead + backing), split into two segments.
- If a line is unintelligible, put `"[unintelligible]"` as text and note it.
- **Transcribe what you hear.** Don't autocorrect grammar; don't fix typos in the singer's lyrics.

### 3.9 `clave_segments` (salsa only)
- An array of `[{start_sec, end_sec, direction, confidence}]`.
- `direction` is one of: `2_3`, `3_2`, `rumba_2_3`, `rumba_3_2`, `n_a`, `unclear`.
- If the clave changes mid-song, add multiple segments. Note the transition in `notes`.
- Use the **son clave** unless you can clearly hear the rumba clave (timba, songo, modern timba often use rumba clave).
- For bachata, this field is `[]` (use `clave_direction: null` in `global`).

### 3.10 `hits`
- An array of `[{time_sec, strength, type, notes}]`.
- `type` is one of: `downbeat`, `accent`, `syncopation`, `break`.
- `strength` is 0–1 (1 = the strongest hit in the song).
- Don't over-annotate. List the 10–20 most important hits per song.

### 3.11 `difficulty_estimate`
- Self-reported ease of annotation per axis.
- Helps us understand which songs will be the "easy wins" vs the "tricky edge cases".

---

## 4. Tools

### 4.1 Recommended toolchain
1. **Sonic Visualiser** (free, open source) — best for waveform + spectrogram + annotation
2. **Audacity** (free) — quick listening + simple labels
3. **Reaper** (commercial, ~$60, free for non-commercial) — best for serious annotation with custom actions
4. **BPM Tap** (web) — quick BPM tapping
5. **Mixed In Key** (commercial, ~$58) — high-quality BPM + key detection
6. **MusicBrainz Picard** (free) — for metadata + acoustic fingerprinting

### 4.2 Recommended workflow
1. **Get the song** (FLAC preferred, 44.1 kHz, 16-bit, mono or stereo).
2. **Acoustic fingerprint** with MusicBrainz Picard to confirm metadata + get BPM + key as starting points.
3. **BPM tap** in BPM Tap to get a second opinion.
4. **Load in Sonic Visualiser** with the spectrogram + waveform visible.
5. **Mark the downbeats** by tapping along. Use the beat toolbar; save as `.svl` file.
6. **Mark the section boundaries** by listening while watching the spectrogram. Use the regions layer.
7. **Transcribe the lyrics** while listening. Use the text layer.
8. **Identify the clave direction** (salsa only). Tap a clave pattern (wooden stick sound) and see if it aligns.
9. **Export everything as JSON** in the §2 schema. (We'll provide an export script for Sonic Visualiser.)
10. **Self-review** by playing the song from each section start — does the annotation feel right?

### 4.3 Time commitment per song
- Listening: 1× playthrough (3–4 min)
- Annotation: 30–60 min for a careful annotator on a typical song
- Edge cases (e.g. weird song structure): up to 2 hours
- **Budget: 50–100 hours total** for the 200-song set if you do it alone.

### 4.4 When to use the "second annotator" workflow
For 20% of songs (40 songs), have a second person annotate independently. Compare:
- If both agree → confidence `high`
- If they disagree by 1–2 seconds → adjudicate, confidence `med`
- If they disagree on section type → adjudicate, mark with `notes: "adjudicated"`
- If they disagree on BPM by > 2 → re-listen, possibly re-annotate from scratch

---

## 5. Quality checks (per song)

Before you save a golden annotation, run through this checklist:

- [ ] All sections are contiguous and non-overlapping
- [ ] First section starts at 0.0
- [ ] Last section ends at `duration_sec` (±0.5s)
- [ ] Section types are from the locked taxonomy
- [ ] BPM is set with confidence
- [ ] Downbeats array is non-empty
- [ ] Lyrics segments are non-overlapping
- [ ] Lyrics language is set
- [ ] Clave is set (salsa) or null (bachata)
- [ ] `stems_present` reflects what you actually heard
- [ ] `intake.annotator_id` is your stable ID
- [ ] `intake.source_sha256` matches the file
- [ ] `intake.annotated_at` is the ISO timestamp

---

## 6. The 5-song pilot (this week)

Before annotating 200, do 5. Pick:
1. **Obsesión** — Aventura (bachata_moderna, 128 BPM, classic)
2. **Propuesta Indecente** — Romeo Santos (bachata_moderna, 132 BPM)
3. **Darte un Beso** — Prince Royce (bachata_moderna, 128 BPM)
4. **Vivir Mi Vida** — Marc Anthony (salsa, 184 BPM, montuno-heavy)
5. **Idilio** — Willie Colón / Héctor Lavoe (salsa_dura, 92 BPM half-time, classic)

These 5 are **diverse** (different styles, BPMs, structures) and **representative** (incluso Dentro uses Obsesión as its demo). Annotate them in 2–3 days, then review the schema and tool workflow before scaling to 200.

---

## 7. File layout (in the repo)

```
golden/
├── README.md                      ← this file
├── songs/
│   ├── f47ac10b-58cc-4372-a567-0e02b2c3d479.flac
│   ├── f47ac10b-58cc-4372-a567-0e02b2c3d479.json
│   └── ...
├── sources/                       ← raw sources before intake
│   └── ...
├── scripts/
│   ├── intake.py                  ← generates song_id + computes sha256
│   ├── validate.py                ← checks a JSON against the schema
│   ├── stats.py                   ← reports coverage (genre, BPM, style)
│   └── ...
└── SCHEMA.md                      ← the JSON schema in machine-readable form
```

### 7.1 The intake script (`scripts/intake.py`)
When you drop a new song into `sources/`, run:
```bash
python scripts/intake.py sources/obsession.flac
# → generates songs/<uuid>.flac, songs/<uuid>.json (skeleton)
```

### 7.2 The validator (`scripts/validate.py`)
Before you commit a golden JSON, run:
```bash
python scripts/validate.py songs/<uuid>.json
# → exits 0 if valid, 1 with error list if not
```

CI runs this on every PR. A failing validation blocks merge.

---

## 8. What we measure from the golden set

Every ML model upgrade is evaluated on this set. Standard reports:

| Metric | Formula | Target v1 |
|---|---|---|
| **BPM MAE** | mean abs error of `bpm` prediction | < 0.5 |
| **Downbeat F1** | F1 of downbeat detection (tolerance ±50ms) | > 0.95 |
| **Section boundary F1** | F1 of section start/end boundaries (tolerance ±1 bar) | > 0.85 |
| **Section type accuracy** | % of sections with correct type | > 0.85 |
| **Clave direction accuracy** (salsa) | % of songs with correct direction | > 0.90 |
| **Stem SDR (vocals)** | mean SDR on vocals stem | > 9 dB |
| **Stem SDR (other stems)** | mean SDR on other stems | > 7 dB |
| **8-count phase correctness** | % of bars with correct downbeat | > 0.95 |
| **Lyrics WER** | word error rate of transcription | < 0.10 |

These are the "we're done" criteria for each phase of the ML pipeline.

---

## 9. License and contribution

The golden set, like the rest of Compás, is **Apache 2.0**. The audio files must be either:
- Public domain
- CC0 / CC-BY / CC-BY-SA (with attribution preserved)
- Self-recorded with explicit release
- Used under fair use for evaluation only (not redistributed)

If you want to contribute songs, the contribution process:
1. Open a PR with the song + JSON in `golden/songs/`
2. Confirm license in the PR description
3. CI runs validation + a basic sanity check (BPM range, section contiguity)
4. A second annotator reviews and either approves or requests changes
5. On approval, the song joins the golden set

---

## 10. Common pitfalls (learned from MIR community)

1. **Trusting the tool's BPM blindly.** Tools are 70–90% accurate. Always confirm by tapping.
2. **Forgetting half-time / double-time.** A song at "64 BPM" with double-time feel is really 128 BPM. Always tap along.
3. **Confusing the song's first beat with the first downbeat.** A count-in (e.g. 4 clicks before the music starts) is not a downbeat. Mark the music's first beat 1.
4. **Marking sections at the wrong granularity.** Don't break every 4 bars. The natural section is 8+ bars unless something clearly changes.
5. **Forgetting to listen with headphones vs speakers.** A subtle perk or fill that's clear on speakers may be inaudible on headphones. Use both.
6. **Annotation drift.** After 4 hours of annotating, your ears are tired and you make mistakes. Take breaks. Don't annotate more than 4 songs per day.
7. **Section type creep.** Stick to the locked taxonomy. If you want a new type, propose it in an issue first.

---

## 11. Questions?

If anything is unclear, open an issue in the repo or ask in the project's discussion forum. Annotation quality determines the quality of the entire ML pipeline — it's worth taking the time to get right.
