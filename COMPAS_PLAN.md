# Project **Compás** — A Plan to Build Something Better Than Dentro

> Working name: **Compás** (Spanish for *beat / rhythm / compass*).
> Goal: a free, open, more accurate, more musical, and richer companion for salsa & bachata dancers (and musicians) than Dentro. **All features free. No paywalls. No business model.**

---

## 0. TL;DR

Dentro is great at one specific thing — splitting a bachata song into 4 stems, mapping real instrument onsets to the 8-count, and overlaying translated lyrics. The plan below takes that kernel and rebuilds it as:

- **More stems** (vocals, requinto, segunda, bass, bongó, güira, "other") via Demucs v4 / Mel-Band-Roformer
- **Deeper musical intelligence** (clave, 8-count, section structure, mambo, soneo, energy, hits, breaks)
- **Pattern recognition** for *dance* (not just instruments): when to turn, when to body-roll, when to do shines
- **Voice understanding** (lyrics, phonetic timing, translations, pronunciation, soneo detection, call-and-response)
- **Web-native PWA** (works on phone, tablet, desktop, no install, offline)
- **Admin & User upload roles** with a clean trust model
- **100% free** because no business — features are gated only by tier of trust, not by money
- **Privacy-first**: heavy audio processing happens client-side (WebGPU/ONNX) where possible

### 0.1 Quick Reference — What We Build, Locked

| | **Bachata** | **Salsa** |
|---|---|---|
| **Stems (target)** | 7: vocals-lead, vocals-back, requinto, segunda, bass, bongo, guira (+clave+palmas residual) | 9–10: vocals-lead, vocals-coro, piano, bass, congas, timbales+cowbell, bongo, clave, maracas+guiro, horns |
| **Sections (target)** | 10: Intro, Verso, Pre-coro, Coro, Mambo, Majae, Soneo, Puente, Breakdown, Outro | 8 + 4 sub: Intro, Verso, Coro-pregón, Coro, Montuno (Mambo, Diablo, Moña, Especial), Soneo, Coda |
| **Clave detector** | optional 3-2 / 2-3 when present | **required 3-2 / 2-3** with confidence + per-bar switches |
| **BPM range** | 100–160 (typical 120–140) | 160–220 |
| **8-count source** | beats 1 & 5 (bass) + 1 (requinto) + 4 (guira) + martillo | piano montuno + bass tumbao + conga tumbao + cowbell chord beat |
| **Musicality curves** | 8 (req melody, martillo, guira, bass drops, vocal activity, hits, energy, sections) | 8 (clave dir, piano, conga, cowbell, horns, vocal, bass drops, sections) |
| **Dance suggestions** | 8 (derecho, mambo, dile que no, enchufla, majae, paseo, corte, soneo) | 4 styles (on1, on2, casino/rueda, LA-style) + sub-section cues |

Full taxonomy in **§1**. Anything not on these lists = out of scope for v1.

---

---

## 1. Locked Genre Specification — Instruments, Sections, Dance Mapping

> This is the canonical, *locked* list. Compás builds **only** for these instruments and sections per genre. Anything outside is out of scope for v1 and only added via taxonomy extension by Admin.

> **Sources (verified via Wikipedia + standard pedagogy)**:
> - *Bachata (music)*: standard 5-instrument group (Requinto, Segunda, Bass, Bongó, Güira); Güira replaced maracas in 1980s.
> - *Salsa music*: standard conjunto instrumentation; sections include Intro / Verso / Coro / Montuno (with Mambo, Diablo, Moña, Especial sub-sections) / Soneo / Coda.
> - *Clave (rhythm)*: Son clave (3-2 / 2-3 direction), Rumba clave.
> - *Cuban son*: two-part form (theme / montuno); mambo as historical predecessor of salsa.
> - *Bachata (dance)*: 8-count basic step with hip check on 4 and 8.

### 1.1 Bachata — Canonical Instruments (5 + variants)

| # | Instrument | Role in the music | Bachata-specific note |
|---|---|---|---|
| 1 | **Requinto** (lead guitar) | Arpeggiated repetitive chord patterns — the *signature* bachata sound | Nylon-string traditional; steel-string modern |
| 2 | **Segunda** (rhythm guitar) | Syncopated chord stabs, "bolero" comping | Often quieter than requinto, harder to isolate |
| 3 | **Bajo / Bass** (electric) | Low-end foundation; emphasizes beats 1 & 5 of the 8-count | Drives the hip motion of the dance |
| 4 | **Bongó** (bongo drums) | Plays the **martillo** pattern — 8 strokes per 8-count (the "double-time feel") | Standard for bolero-style bachata |
| 5 | **Güira** (metal scraper) | Steady 8th-note subdivisions; the **metronome** of bachata | Replaced maracas in the 1980s |
| 6 | **Tambora** (Dominican drum) | Replaces bongó in **merengue-based bachata** | Only when style = "merengazo" |
| 7 | **Clave** (two hardwood sticks) | Optional rhythmic backbone | 3-2 vs 2-3 direction matters when present |
| 8 | **Lead vocals** (singer) | Tells the romantic story | Front-and-center of the mix |
| 9 | **Backing vocals / coros** | Harmony, "oh-oh-oh" responses, second voice | Present in coro and soneo |
| 10 | **Palmas / hand claps** | Layered in modern / urban / remix bachata | Optional, often absent |
| 11 | **Synth pads / drum machine** | Modern/urban bachata (Urbana, Bachatango) | Optional layer, often replacing real percussion |

**Compás stem target for bachata = 7 stems**:
`vocals-lead` · `vocals-back` · `requinto` · `segunda` · `bass` · `bongo` (or `tambora` if style=merengazo) · `guira` (+ `clave+palmas+other` combined into one residual stem).

> *Insight*: Dentro already picks the right 4 of these 7 (requinto, bongo, guira, bass) plus vocals-lead. The **three missing stems** are `segunda` (compete with requinto), `vocals-back` (choruses), and the `clave+palmas` residual. Separating them is the largest single quality jump.

### 1.2 Bachata — Canonical Sections

| Section | Bars (typical) | What you hear | Dance interpretation |
|---|---|---|---|
| **Intro** | 4–16 | Requinto + bass (no vocals); often a riff of the coro | Dancers enter the floor, find position |
| **Verso** (verse) | 8–16 | Lead vocals + full band; storytelling, lower energy than coro | Basic step, partner connection, body movement |
| **Pre-coro** *(optional)* | 4 | Build, melodic lift, anticipation | Pre-emptive turn, weight shift |
| **Coro** (chorus) | 8–16 | Singable hook, full energy, repeated lyrics | Same footwork, more pronounced hip motion |
| **Mambo** | 2–8 | **Vocal break OR a big hit OR a bass fill**; often 1 bar of break then back | **Cross-body lead with turns** — the dancer's "show-off" moment |
| **Majae / Majao** | 4–8 | Open-position: vocals drop, percussion leads, requinto vamps | **Open-position footwork, shines, body rolls** (dancers separate but stay hand-connected) |
| **Soneo** | 8–32 | Singer improvising over coro vamp; high energy, rhythmic vocal play | **Shines, footwork, freestyle, partner tricks** — music is "open" |
| **Puente** (bridge) | 4–8 | Chord change (often relative major/minor); melodic break | **Dips, body isolations, romantic hold** |
| **Breakdown** | 2–4 | Instrumentation drops near-silence, then a hit; just requinto + bass | **Stop, dip, body roll, dramatic pose** |
| **Outro / Coda** | 4–16 | Vamp on coro, or fade | Wind down, final pose, exit |

### 1.3 Bachata — Section-to-Instrument Matrix (loudest stem per section)

This is also a **detector signal**: "vocal activity drops AND bass+bongo energy stays high AND requinto stops" = mambo/majae candidate.

| Section | Dominant stems | Quiet / silent |
|---|---|---|
| Intro | requinto, bass | vocals |
| Verso | requinto, segunda, bass, bongo, guira | — |
| Pre-coro | all (lifted) | — |
| Coro | requinto, vocals-lead, bongo, guira, bass | — |
| Mambo | bass, bongo, segunda | vocals-lead (usually) |
| Majae | bongo, guira, bass, segunda | vocals |
| Soneo | vocals-lead, vocals-back, bass, bongo, guira | — |
| Puente | requinto, segunda, bass (chord change) | percussion drops |
| Breakdown | requinto, bass (minimal) | everything else |
| Outro | requinto, bass, vocals | — |

### 1.4 Bachata — Musicality Mapping (which instrument cues which dance move)

Per-bar, compute these curves:

| Curve | Source stem | What it cues in the dance |
|---|---|---|
| **Requinto melody intensity** | RMS + spectral centroid on `requinto` | Body movement, turns, weight changes |
| **Bongó martillo density** | onset count on `bongo` | Footwork timing (double-time feel) |
| **Güira subdivision** | 8th-note density on `guira` | The 1-2-3-4-5-6-7-8 metronome |
| **Bass drops** | onset picker on `bass` (peaks at beats 1 & 5) | Dips, leans, big body movement |
| **Vocal activity** | RMS on `vocals-lead` | Story (close) vs open (shines) |
| **Hit detector** (Daccent) | peak picker on spectral flux (full mix) | Body wave / isolation / stomp beats |
| **Energy** | RMS on full mix | Overall push: gentle vs intense |
| **Section change** | section model | Type of move: basic / mambo / shines / sensual |

### 1.5 Salsa — Canonical Instruments (10–12 in a standard conjunto)

| # | Instrument | Role | Salsa-specific note |
|---|---|---|---|
| 1 | **Clave** (two hardwood sticks) | The rhythmic backbone — *"the heart of salsa"* | 3-2 / 2-3 direction is critical to communicate |
| 2 | **Congas** (tumbadoras) | **Tumbao** rhythm (off-beats 2, 4, 6, 8) — the "on2" timing | Three drums: quinto (lead), conga, tumba |
| 3 | **Timbales** | Bell (cencerro) pattern on the drum side | Two drums + cencerro attached |
| 4 | **Bongó** | Lead drum; improvises; plays bell during montuno | Smaller than congas, higher pitch |
| 5 | **Cencerro** (cowbell) | **Chord beat** (1, 3, 5, 7) — the "on1" timing | Often mounted on timbales |
| 6 | **Maracas** | Steady 8th-note subdivisions | Clave-neutral |
| 7 | **Güiro** | Steady 8th-note subdivisions | Clave-neutral |
| 8 | **Bajo** (electric or upright bass) | Tumbao-based line | "Independent of clave" but harmonically aligned |
| 9 | **Piano** | **Montuno** rhythm (the 8-count vamp) | Defines the dance section |
| 10 | **Trumpet(s) / horn section** | Melodic lines, mambo, diablo | 2–4 horns typical |
| 11 | **Lead vocals** (sonero) | **Soneo** — improvisation over the montuno | The story-teller |
| 12 | **Coro** (chorus singers) | Call-and-response | "¡Azúcar!" |

**Compás stem target for salsa = 9–10 stems**:
`vocals-lead` · `vocals-coro` · `piano` · `bass` · `congas` · `timbales+cowbell` · `bongo` · `clave` · `maracas+guiro` · `horns` (combined).

### 1.6 Salsa — Canonical Sections (Wikipedia-confirmed)

| Section | Bars (typical) | What you hear | Dance interpretation |
|---|---|---|---|
| **Intro** | 4–16 | Piano montuno + bass, building; sometimes horns; claves often enter late | Dancers enter, find the 1 |
| **Verso** (verse) | 8–16 | Lead vocalist + full band, bongó improvises | Partner work, basic step, on1 or on2 |
| **Coro-pregón / Pre-coro** | 4 | Call to the chorus, coro singing the hook | Anticipation |
| **Coro** (chorus) | 8 | Singable hook, call-and-response with coro | Same footwork, sing along |
| **Montuno** | 16–64+ | The 8-count vamp; **piano montuno + bass tumbao + conga tumbao** | THE dance section; partner work, shines, turn patterns |
| ↳ **Mambo** *(sub of montuno)* | 4–16 | Horn-driven, often a horn solo, percussion goes wild | **Shines moment — partner separates, both shine** |
| ↳ **Diablo** *(sub)* | 4–8 | High-energy, complex rhythm, all instruments pushing | Fast footwork, complex shines |
| ↳ **Moña** *(climax)* | 4–8 | Peak of the song, vocals + horns together | Climax of the dance, biggest move |
| ↳ **Especial** | 4–8 | A "special" arrangement, key change or new vamp | Big trick, dip, lift |
| **Soneo** *(interleaved with montuno)* | 8–32+ | Lead singer improvising over the montuno vamp | Shines, footwork, freestyle |
| **Coda / Outro** | 4–16 | Final vamp, often a hit then end | Big finish, dramatic pose |

### 1.7 Salsa — Section-to-Instrument Matrix

| Section | Dominant stems | Quiet / silent |
|---|---|---|
| Intro | piano, bass, horns | congas, bongo |
| Verso | vocals-lead, bass, congas, bongo, piano | coro |
| Coro | vocals-lead, vocals-coro, congas, piano, bass | horns (mostly) |
| Montuno | piano, bass, congas, timbales, bongo | vocals-lead |
| ↳ Mambo | horns, timbales, bongo, congas, bass | vocals, piano (simplifies) |
| ↳ Diablo | all pushing | — |
| ↳ Moña | vocals-lead, horns, all | — |
| Soneo | vocals-lead, piano, bass, congas | horns (usually) |
| Outro | piano, bass, timbales | vocals, horns |

### 1.8 Salsa — Musicality Mapping

| Curve | Source stem | What it cues |
|---|---|---|
| **Clave direction (2-3 / 3-2)** | onset pattern on `clave` + `cowbell` | Dancer "side of the bar" — critical for On2 |
| **Piano montuno density** | onset count on `piano` | The main 8-count; everything aligns to this |
| **Conga tumbao** | onset pattern on `congas` | **On2 timing** (off-beats 2, 4, 6, 8) |
| **Cowbell (cencerro)** | onset count on `timbales+cowbell` | **On1 timing** (1, 3, 5, 7) |
| **Horn hits** | peak picker on `horns` | Big accents, energy spikes, climax |
| **Vocal activity (soneo vs coro)** | RMS on `vocals-lead` | Narrative vs open-for-shines |
| **Bass drops** | onset picker on `bass` | The "drop" — beat to anticipate for the next phrase |
| **Section change** | section model | Switch from partner work to shines |

### 1.9 Why This Beats Dentro

| Aspect | Dentro | Compás |
|---|---|---|
| Stems (bachata) | 4 (requinto, bongo, guira, bass) + vocals | **7** (adds segunda, vocals-back, clave/palmas residual) |
| Stems (salsa) | ❌ not supported | **9–10** |
| Section detection | Static label (Derecho/Mambo/Majae) | **Dynamic, 10 sections per genre with confidence** |
| Mambo sub-sections (salsa) | ❌ | **Mambo / Diablo / Moña / Especial** |
| Clave direction (2-3 vs 3-2) | ❌ | **Detected + shown to dancer** |
| Musicality curves | ❌ | **8 per genre** (instrument → dance mapping) |
| Hit detection | ❌ | **Per-beat hit indicator** for body accents |
| Vocal activity → "open for shines" | ❌ | **Real-time badge** |
| BPM range support | Bachata only (~120–140) | **Bachata + salsa (160–220) + merengue** |
| Tap to jump to a word | partial (scroll) | **Tap to jump + vocal pitch line lights up** |

---

## 2. Dentro: What It Does Well, Where It Falls Short

### What it does well (keep these ideas)
- Stem isolation with per-stem mute/solo
- Visual mapping of onsets onto a fixed 8-count grid (the "gem" lane per instrument)
- 8-count + tempo display (e.g. "128 BPM · double-time feel")
- Section flag in corner (Derecho / Mambo / Majae)
- Lyrics + word-by-word translation
- A small curated song library

### Where it falls short (every one of these is a *Compás* win)
| Dentro limitation | Compás improvement |
|---|---|
| Only **4 stems** (vocals, requinto, bass, drums) | **6–8 stems** (vocals, requinto, segunda, bass, bongó, güira, hand-claps, other) |
| **8-count is shown but not validated** — assumes "every gem lands on the 8-count" | **8-count validator** with confidence score per bar; auto-corrects phase drift |
| **Section labels (Mambo/Derecho/Majae) are static** | **Dynamic section detection** (intro / verse / coro / mambo / puente / soneo / outro) with confidence |
| **No clave / tumbao / martillo detection** | **Clave detector** (2-3 / 3-2), **bongó martillo** tracker, **güira** density curve |
| **Lyrics: one translation, no phonetics** | **Multi-language translation** + **IPA phonetics** + tap-to-hear + soneo/coro detection |
| **No dance pattern suggestions** | **Pattern coach**: per-section move suggestions (basic step, cross-body lead, turn patterns, shines) |
| **No "hits"** (emphasized beats for body movement) | **Hit detector** — where to add a body wave/isolation/foot stomp |
| **iOS app only (from what the screenshots show)** | **Web PWA** — phone, tablet, desktop, offline |
| **Own-music upload is Pro ($8/mo), 15 songs/month** | **Unlimited uploads, free, forever** |
| **No practice loops, no speed control, no A/B** | **Loop region + speed (50%–150%, pitch-preserved) + pitch shift + A/B** |
| **No chord/key detection** | **Chord + key detection** synced to the 8-count |
| **No "musicality" curves (energy, density, drop)** | **Energy / onset-density / spectral-flux / danceability curves** below the gem grid |
| **Lyrics are scroll-only** | **Karaoke-style follow** with auto-scroll + tap-to-jump |
| **Onset gem lane is fixed pitch** | **Pitch-aware gem lane** (vertical position = MIDI pitch of the hit) — see mambo bass drops visually |
| **No export of stems or analysis** | **Export stems (FLAC), MIDI 8-count, CSV annotations, shareable analysis link** |

---

## 3. Personas & Roles

| Role | Capabilities |
|---|---|
| **Guest** (not logged in) | Browse public library, play songs, see visualization, see translations. **No upload.** |
| **User** (logged in, default) | Everything Guest can do + **upload their own songs** (unlimited, free), build private playlists, export stems/analysis, comment / annotate. |
| **Trusted User** (auto-promoted by behaviour: clean uploads, no abuse, N approved uploads) | Same as User + can submit songs to the **Community Library** (subject to moderation). |
| **Moderator** (volunteer / appointed) | Approve / reject Community Library submissions, hide abuse, ban abusers, lock annotations. |
| **Admin** | Full control: feature flags, model versions, role assignment, library curation, DB access, audit log, kill switch for ML jobs, roll back model, manage taxonomies (genres, sections, instruments), see global analytics. |
| **System** (bot) | Runs ML pipeline, writes back analysis, no UI. |

**Why this matters for "all features free"**: trust-tier gates *contribution*, not *consumption*. Anyone can use every feature; only the act of publishing to the global library requires trust. No money involved.

---

## 4. The "100% Accurate & Reliable" Promise — How We Get There

> "100% accurate" is impossible — but **100% reliable** (consistent, predictable, never silently wrong) is achievable.

### 3.1 Multi-pass analysis with confidence scoring
Every analysis output is computed **multiple ways** and **reconciled**:

- **8-count phase**: Beat-Transformer downbeat → librosa onset envelope cross-correlation against canonical bachata kick pattern → manual anchor. If disagree, **show "uncertain" badge** instead of forcing a wrong answer.
- **BPM**: Beat-Transformer + librosa + essentia + autocorrelation. Output: `{bpm, bpm_alt, confidence, stability_curve}`.
- **Section boundaries**: SA3 structure model + energy + vocal-density + drop detection. Boundaries only commit if ≥2 signals agree within tolerance.
- **Stem separation**: Demucs v4 + Mel-Band-Roformer ensemble. Track per-stem SDR (signal-to-distortion ratio). If SDR < 8 dB, mark stem as "low-quality" and exclude from gem detection.

### 3.2 Confidence UI
Every UI element has a **confidence state**: green / yellow / red. The user always knows what's a guess. This is what Dentro doesn't do and what makes a tool trustworthy.

### 3.3 Determinism
- All ML models pinned by **hash**, not name. Model upgrades are explicit.
- Random seeds in separation fixed per run; same input → same output.
- Analysis results stored immutably; re-analysis is a *new* version, never overwrites.

### 3.4 Self-test suite
- A **golden test set** of ~200 hand-annotated bachata & salsa tracks with known BPM, 8-count, sections, and stem ground truth.
- CI runs every model upgrade against the golden set. Numbers must not regress > 2% before merging.

---

## 5. Core Capabilities — Deep Dive

### 4.1 Stem Separation — Genre-Specific Stems (per §1.1 and §1.5)

> **Read §1 first** — that section is the locked taxonomy. This section is the *how*.

**Demucs's default 4-stem (vocals/drums/bass/other) is not enough.** Both bachata and salsa pack 5–10 critical instruments into Demucs's "other" and "drums" buckets. We need to **further split** those buckets with per-instrument classifiers.

**Models (late-2025 SOTA):**
1. **Demucs v4 (`htdemucs_ft`)** — Meta, fine-tuned, 4-stem (vocals/drums/bass/other). The workhorse.
2. **Demucs v4 (`htdemucs_6s`)** — 6-stem (vocals/drums/bass/{guitars}/{piano}/{other}). Pre-separation stage that gives us piano and guitars as separate buckets — critical for salsa.
3. **Mel-Band-Roformer** (Kim et al., 2023–2024) — current SDR leader for vocals & accompaniment splits. Use for clean vocal isolation.
4. **BS-Roformer** (Band-Split Roformer) — alternative that's shown stronger results in 2024 on some stem types.
5. **Ensemble**: per-frequency-band best (winner-take-band fusion) of Demucs + Roformer → typically +1 to +2 dB SDR over either alone.

**Compás stem targets (driven by §1.1 and §1.5):**

#### Bachata (7 stems)
| Compás stem | How we get it from Demucs+Roformer | Notes |
|---|---|---|
| `vocals-lead` | Roformer vocals − Demucs lead-vocal residual | cleanest lead vocal |
| `vocals-back` | Demucs vocals − Roformer lead | the "oh-oh-oh" |
| `requinto` | Demucs 6s `{guitars}` band 250 Hz–4 kHz + requinto-onset-DNN | the *signature* bachata sound |
| `segunda` | Demucs 6s `{guitars}` band 80–250 Hz + segunda-onset-DNN | harder to isolate; needs ML |
| `bongo` | Demucs `{drums}` via YAMNet fine-tuned on bongó samples | detects martillo pattern |
| `guira` | Demucs `{drums}` high-pass > 4 kHz + onset-DNN | metallic, very high |
| `bass` | Demucs `{bass}` + onset-DNN | beats 1 & 5 emphasis |
| `clave+palmas+other` | residual bucket | merged; clave & palmas rarely both present |

**Note on Tambora**: if the style classifier tags a song as "merengazo" (§1.1 row 6), `bongo` is renamed to `tambora` and the detector is swapped.

#### Salsa (9–10 stems)
| Compás stem | How we get it | Notes |
|---|---|---|
| `vocals-lead` | Roformer vocals − Demucs lead | the sonero |
| `vocals-coro` | Demucs vocals − Roformer lead | the chorus singers |
| `piano` | Demucs 6s `{piano}` bucket | montuno rhythm |
| `bass` | Demucs `{bass}` | tumbao |
| `congas` | Demucs `{drums}` per-hit classifier (low-pitched, 3-drum pattern) | tumbao |
| `timbales+cowbell` | Demucs `{drums}` per-hit classifier (mid-pitched, bell) | cencerro mounted on timbales |
| `bongo` | Demucs `{drums}` per-hit classifier (high-pitched) | |
| `clave` | Demucs `{other}` onset-DNN tuned to 2 hard sticks | **critical — drives 2-3 vs 3-2** |
| `maracas+guiro` | Demucs `{other}` onset-DNN | both clave-neutral |
| `horns` | Demucs 6s `{other}` freq-band 200 Hz–2 kHz + transient picker | 2–4 trumpet/trombone section |

**Output format**: FLAC (lossless) for download, Opus 96 kbps for streaming playback. Per-stem loudness normalized to −16 LUFS (Spotify-style).

**Where it runs:**
- **Fast path (client)**: ONNX Runtime Web + Transformers.js for Roformer-Tiny on WebGPU → ~3× real-time on M-series MacBook, ~1.5× on iPhone 15 Pro. Good for < 5 min clips, for "preview" stems, and for the 4 main stems only.
- **Slow path (server)**: GPU pool (NVIDIA L4 or A10) running full PyTorch ensemble. Used for full library + user uploads of > 5 min. Yields all 7 (bachata) or 9–10 (salsa) stems.

### 4.2 Beat, Tempo, 8-Count, Downbeat

**Models:**
- **Beat-Transformer** (Heydari et al., ISMIR 2023) — beats + downbeats, transformer-based, SOTA on GTZAN, Ballroom, Beatles.
- **librosa `beat.beat_track`** — fallback.
- **essentia `RhythmExtractor2013`** — fallback.

**Bachata-specific 8-count detector (custom):**
- Take downbeats (every 4 beats) as candidate 8-count starts.
- Score each candidate by: (a) does Requinto onset land on beat 1? (b) does Güira onset land on beat 4? (c) does Bass onset land on beats 1 & 5? (d) does Bongó martillo follow the canonical 8-stroke pattern?
- Take the highest-scoring phase, then drift-correct with a Viterbi-style search over a ±250 ms window.

**Output:**
```json
{
  "bpm": 128.0,
  "bpm_alt": [64.0, 256.0],
  "first_8_count_start": 4.812,
  "phase_confidence": 0.94,
  "phase_stability": [0.91, 0.93, 0.94, ...],
  "downbeats": [0.0, 1.875, 3.75, ...]
}
```

### 4.3 Section / Pattern Detection (driven by §1.2 and §1.6)

> **Read §1 first.** The locked taxonomies are: bachata = 10 sections (§1.2); salsa = 8 top-level sections + 4 montuno sub-sections (§1.6). The detectors below target exactly those.

**Models:**
- **SA3 / All-In-One Music Structure Transformer** for coarse sections.
- **Custom rule layer** driven by the §1.3 (bachata) and §1.7 (salsa) section→instrument matrices.

#### Bachata section detectors (10)
| Section | Detector |
|---|---|
| Intro | First 4–16 bars; vocals-lead RMS ≈ 0; requinto + bass active |
| Verso | vocals-lead active; energy < median; no coro pattern (lyrics non-repeating) |
| Pre-coro | vocals-lead active; rising pitch contour; +1 semitone avg pitch shift vs verso |
| Coro | vocals-lead active; energy > median; repeated lyric pattern |
| Mambo | vocals-lead drops out for 0.5–2 bars; bass+seconda hit; bongo density peaks |
| Majae | vocals silent; bongo+guira+bass dominate; requinto vamps on single chord |
| Soneo | vocals-lead pitch variance > threshold; low lyric repetition; duration variance high |
| Puente | chord progression changes (relative major/minor); often percussion drops out |
| Breakdown | onset density < 20% of median for > 2 bars, then a hit |
| Outro | last 4–16 bars; energy ramp-down OR repeating coro vamp |

#### Salsa section detectors (8 + 4 sub-sections)
| Section | Detector |
|---|---|
| Intro | First 4–16 bars; claves often enter late; piano+horns start; congas silent |
| Verso | vocals-lead active; bongo improvises; coro quiet |
| Coro-pregón | coro singing hook; vocals-lead silent; short (4 bars) |
| Coro | vocals-lead + vocals-coro active; call-and-response detected |
| Montuno | piano+congas+bass all active with montuno+tumbao+steady patterns; 8-count vamp detected; usually > 16 bars |
| ↳ Mambo (sub) | inside Montuno; horns dominant; vocals+piano simplify; percussion pushes harder |
| ↳ Diablo (sub) | inside Montuno; all-stem onset density > 1.5× montuno median; horn transients high |
| ↳ Moña (sub) | inside Montuno; peak RMS; vocals + horns together; often last 4–8 bars of montuno |
| ↳ Especial (sub) | inside Montuno; key change OR new vamp OR full-ensemble break |
| Soneo | inside (or after) Montuno; vocals-lead improvising over montuno vamp; pitch variance high |
| Coda / Outro | last 4–16 bars; energy ramp-down or final hit |

#### Bachata dance pattern vocabulary (dancer's terminology, used in UI labels)
- **Derecho** (straight 8-count, basic)
- **Mambo** (cross-body)
- **Dile que no** (right-hand turn pattern)
- **Enchufla** (cross-body with double-spin)
- **Majae / Majaheo** (shadow position with footwork)
- **Paseo** (walk-around)
- **Corte** (stop / hold)
- **Soneo / Montuno** (free musical moment)

#### Salsa clave (per Wikipedia §1)
- **Son clave 2-3** (most salsa) — chord progression begins on the 2-side
- **Son clave 3-2** — chord progression begins on the 3-side
- **Rumba clave** (less common, used in some modern/timba)
- Output: `{ direction: "2-3", confidence: 0.93, switches: [{ bar: 96, from: "2-3", to: "3-2" }] }`

**Implementation**: rule layer + small classifier (gradient-boosted trees on engineered features) trained on the §11 golden test set of 200 hand-labelled bachata & salsa tracks.

### 4.4 Voice, Lyrics, Translation, Phonetics

**Pipeline:**
1. **Transcription**: OpenAI **Whisper large-v3** (or Distil-Whisper for speed) → raw text + per-segment timestamps.
2. **Forced alignment**: **Stable-TS** or **WhisperX** → word-level (and where possible, phoneme-level) timestamps.
3. **Language ID**: whisper-detected + verify with `langdetect`.
4. **Translation**: **NLLB-200-distilled-600M** (Meta, 200+ languages) for the translation line. Multiple target languages allowed.
5. **Phonetics**: **espeak-ng** or **G2P** (e.g. `g2p_en`, `phonemizer`) for IPA. Dancer-tap on a word → hear the syllable.
6. **Vocal-type classifier**: lead / backing / coro / soneo / ad-lib. Per-word label.
7. **Pitch contour**: librosa `pyin` (or CREPE) → MIDI pitch per 10 ms. Render as a thin colored line over the gem grid (very pretty, very useful for musicality).
8. **Soneo detector**: variance in pitch + low lyric-repetition + improvisation in duration → flag segment as soneo.

**Display:**
- Lyrics panel auto-scrolls; current line is the lead, current word highlighted, second line underneath is translation.
- Phonetic line appears below on tap.
- Mini piano-roll shows pitch of lead vocal over each bar.

### 4.5 Musicality Engine — what dancers actually *feel*

> The full mapping of instrument → dance cue is **locked** in §1.4 (bachata) and §1.8 (salsa). This section is the *how* (curves, detectors, UI rendering).

The engine computes per-bar, per-stem signals and renders them as a **musicality strip** below the gem grid. All curves are normalized to 0–1 over the whole song so they're visually comparable.

| Curve | Source | What it tells the dancer |
|---|---|---|
| **Energy (RMS)** | per 8-count on full mix | When to push body movement, when to be subtle |
| **Onset density** | sum of onsets per beat on full mix | When the rhythm is "busy" → footwork time |
| **Spectral flux** | librosa on full mix | When a new sound starts → accent / hit |
| **Vocal activity** | vocal energy | When the story is being told (vs when the music is open for shines) |
| **Percussion density** (bongó + güira + bass) | per stem | "How danceable is this exact bar" |
| **Hits** (Daccent) | peak picker on flux | The emphasized beats where dancers add body movement (a bachata/salsa staple) |
| **Drop probability** | classifier on 4-bar window | Forecast where the music is about to break |
| **Phrase boundaries** | every 4 or 8 bars | Helps dancers plan their moves |
| **Clave (2-3 / 3-2)** with confidence | bongó + cowbell onset pattern | Critical for salsa; "play on the right side of the bar" |

**Why this matters**: a bachata dancer wants to know *when the music opens up so I can stop dancing with my partner and do footwork*. That's the vocal-activity curve + drop detector.

### 4.6 Pattern Coach (Dance Moves, not audio patterns)

This is the only place we leave pure audio and enter choreography. We do **not** teach dance moves via video. Instead we *suggest patterns* per detected section.

**Logic** (uses §1.2 / §1.6 section labels directly):

#### Bachata suggestions
| Detected section | + musicality | Suggestion |
|---|---|---|
| Intro | any | "Get into position / find your partner" |
| Verso | vocal_activity high | "Close, basic step, body movement" |
| Pre-coro | rising pitch | "Anticipate turn" |
| Coro | energy high | "More pronounced hip motion, basic step" |
| Mambo | bass hit detected | "Cross-body lead with 1 turn" |
| Majae | open position, percussion-led | "Open-position footwork, shines" |
| Soneo | vocals improvising | "Partner shines / freestyle" |
| Puente | chord change | "Dips, body isolations, romantic hold" |
| Breakdown | silence then hit | "Stop, dip, body roll, dramatic pose" |
| Outro | energy ramping down | "Wind down, final pose" |

#### Salsa suggestions
| Detected section | + musicality | Suggestion |
|---|---|---|
| Intro | any | "Find the 1 (or 2), get into position" |
| Verso | vocal_activity high | "Partner work, basic step, on1 or on2" |
| Coro-pregón | coro hook | "Anticipate the coro" |
| Coro | call-and-response | "Basic step, sing along" |
| Montuno | piano+conga tumbao detected | "Continuous partner work, turn patterns" |
| ↳ Mambo (sub) | horns dominant | **"Shines — partner separates, both shine"** |
| ↳ Diablo (sub) | high onset density | "Fast footwork shines" |
| ↳ Moña (sub) | peak RMS | "Climax — biggest move" |
| ↳ Especial (sub) | key change | "Big trick, dip, lift" |
| Soneo | vocals improvising | "Shines, footwork, freestyle" |
| Coda / Outro | energy ramp-down | "Big finish, dramatic pose" |

Suggestions are pulled from a curated taxonomy of ~80 patterns (40 bachata + 40 salsa), each with a difficulty tag (beginner / intermediate / advanced), a name, and a 1-line description. **User can disable this entirely.** It's a feature, not a nag.

We do NOT show video. The dancer uses their own body vocabulary; we just tell them *what kind of moment it is*.

### 4.7 Practice Tools (free, unlimited)

- **Loop region** (drag-select any bars; A-B repeat)
- **Speed** 50%–150% (phase-vocoder, pitch-preserved; PhaseVocoder in Soxr / Rubber Band)
- **Pitch shift** ±6 semitones (so you can sing along in your range, or train your ear in another key)
- **Metronome** with selectable subdivisions (8th, 16th, martillo pattern, clave pattern)
- **Click track on/off** that locks to the 8-count (visual + audio, with the *bongó martillo* as the audible click — trains the *right* internal clock for bachata)
- **Compare A/B** between original and a stem-mix the user built
- **Build a custom mix** (volume sliders per stem) and save as a "mix preset" per song
- **Mute-the-vocal-while-keeping-the-rhythm** (Dentro's "Solo the percussion" feature, but more reliable)
- **Count-in**: 1 bar of click at the section boundary
- **Slow-down to a specific section** to study a tricky coro

### 4.8 Library, Search, Playlist

- Full-text search across song title / artist / album / lyrics / translations
- Filter: genre (bachata / salsa / merengue / cumbia / kizomba / timba), style (romantic / urban / traditional / mambo / bachatango), BPM range, key, year
- "Songs with mambo at 1:30" search via structured sections
- Smart playlists: "Songs I can dance basic to in this tempo", "Songs with soneo"
- Library types:
  - **Curated** (admin-loaded, high-quality analysis)
  - **Community** (trusted-user-submitted, mod-approved)
  - **My uploads** (private, fully featured, never seen by others)

---

## 6. System Architecture

### 5.1 High-level diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                              BROWSER (PWA)                             │
│                                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  React 19 /  │  │  Web Audio   │  │  Pixi.js     │  │  Service    │ │
│  │  SvelteKit 2 │  │  + Tone.js   │  │  WebGL2 view │  │  Worker     │ │
│  │  UI layer    │  │  engine      │  │              │  │  (offline)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                 │                 │                 │        │
│         └───── ONNX Runtime Web (Roformer-tiny, Whisper-tiny) ──┘       │
│                              │                                         │
└──────────────────────────────┼─────────────────────────────────────────┘
                               │ HTTPS / WebSocket
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          EDGE (Cloudflare)                             │
│  - CDN for static assets + cached stems (R2 mirror)                    │
│  - WAF / rate limit / bot protection                                   │
│  - Cloudflare Workers for auth + upload signing                        │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         API (FastAPI, Python 3.12)                     │
│  - Auth (Lucia / Supabase Auth)                                        │
│  - Upload (presigned URLs to R2)                                       │
│  - Song CRUD                                                           │
│  - Library search (Meilisearch)                                        │
│  - Analysis job submission                                             │
│  - Annotation / community moderation                                   │
└──────┬───────────────────────┬───────────────────┬─────────────────────┘
       │                       │                   │
       ▼                       ▼                   ▼
┌──────────────┐      ┌──────────────────┐    ┌──────────────────┐
│  PostgreSQL  │      │  Redis 7         │    │  Meilisearch     │
│  (metadata,  │      │  (cache, queue,  │    │  (search index)  │
│   users,     │      │   rate limits)   │    │                  │
│   analyses)  │      │                  │    │                  │
└──────────────┘      └────────┬─────────┘    └──────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     ML PIPELINE (GPU workers)                          │
│                                                                        │
│  Stage 1: preflight — duration, format, loudness normalization          │
│  Stage 2: stem separation — Demucs v4 htdemucs_ft + Roformer ensemble  │
│  Stage 3: beat / downbeat / BPM — Beat-Transformer                    │
│  Stage 4: 8-count + clave — custom bachata / salsa layer               │
│  Stage 5: structure / sections — SA3 + custom rules                    │
│  Stage 6: vocals / lyrics / pitch — Whisper large-v3 + pyin            │
│  Stage 7: musicality curves — onset density, energy, flux, drops       │
│  Stage 8: validate against golden set; if SDR/accuracy low → flag      │
│  Stage 9: write back to DB as immutable analysis version               │
│                                                                        │
│  Orchestrator: Dramatiq (Python) or BullMQ (Node)                      │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     STORAGE (Cloudflare R2)                            │
│  - originals/{user_id}/{song_id}/source.flac                           │
│  - stems/{song_id}/{v,rv,rq,s2,bass,bongo,guira,clave,...}.flac        │
│  - analysis/{song_id}/v{version}.json                                  │
│  - waveform/{song_id}/peaks.json (for fast rendering)                  │
│  - mp3 previews at 96 / 192 kbps for streaming                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Why this stack

- **Web PWA**: zero install, cross-platform, push notifications, offline cache of recently played songs. Beats native app install friction.
- **ONNX Runtime Web + WebGPU** for client-side heavy ML: privacy, latency, no server cost for the user.
- **Cloudflare R2**: zero egress fees — important because audio is large and we'll serve stems to many users.
- **Postgres + JSONB** for analysis data: easy to evolve the schema, version analyses, query sections.
- **Meilisearch**: typo-tolerant search across lyrics + translations + metadata. Sub-50ms.
- **Dramatiq** for ML job orchestration: Python-native, retries, dead-letter, scheduled, with Redis as broker.
- **FastAPI**: async-first, type-hints, OpenAPI generated, great ML ecosystem.
- **Web Audio + Tone.js + Pixi.js**: best-in-class audio + visualization in browser.

### 5.3 Auth & Roles (Admin + User upload requirement)

- Email + password (Argon2id) OR OAuth (Google, Apple).
- Roles stored in `users.role` enum: `guest | user | trusted | mod | admin`.
- Server-side **per-route RBAC middleware** (FastAPI dependency) checks role.
- Admin actions are **double-logged** (general audit log + admin_specific log).
- Uploads:
  - **User upload**: signed-URL POST to R2, max 100 MB per file, 30 min duration, formats: FLAC / WAV / MP3 / M4A / OGG. Free, unlimited count, stored under `users/{user_id}/`.
  - **Admin upload**: same, but writes to `curated/` instead of `users/`. Admin can edit metadata after, force re-analysis with a different model, mark as "demonstration" (no analysis allowed to fail publicly), pin to homepage.
  - **Trusted user** can request "publish to community" — goes to moderation queue. Mods approve/reject with reason.

### 5.4 Reliability patterns

- **Idempotent analysis jobs**: `(song_id, model_version, params_hash)` is the job key. Re-running the same job is a no-op.
- **All analysis writes are immutable + versioned**: `analysis_v1.json`, `analysis_v2.json`. UI can show "we re-analyzed this song with model X; here is the diff".
- **Graceful degradation**: if stems are low-quality, the gem grid still works (onset detection on the mix). If lyrics fail, hide the lyrics panel, don't block the rest.
- **Circuit breaker** on the ML API: if 5 jobs in a row fail, mark service as degraded, show banner.
- **Feature flags** (Unleash or self-hosted): Admin can toggle "Roformer model" on/off per request cohort.
- **Per-model kill switch** in admin dashboard.

---

## 7. Tech Stack — Concrete Versions

| Layer | Choice | Version (early 2026) | Why |
|---|---|---|---|
| Frontend framework | **SvelteKit 2** (or Next.js 15) | 2.x / 15.x | SvelteKit smaller bundle, better PWA; Next.js if SEO matters for marketing pages |
| UI components | Bits UI (Svelte) / shadcn-svelte + Tailwind v4 | latest | Accessible, theme-able |
| Audio engine | **Tone.js** + raw Web Audio | 15.x | Scheduling + effects |
| Waveform | **WaveSurfer.js v7** | 7.x | Regions, plugins, fast |
| Visualization | **Pixi.js v8** | 8.x | WebGL2, 60fps at 10k+ gems |
| ML in-browser | **ONNX Runtime Web** + **Transformers.js v3** | latest | WebGPU, model hub |
| Backend | **FastAPI** + **uvicorn** | 0.115+ / 0.32+ | Async, type-safe, OpenAPI |
| Workers | **Dramatiq** + Redis | 1.17+ | Python-native, reliable |
| DB | **PostgreSQL 16** | 16 | JSONB, FTS, mature |
| Cache / queue | **Redis 7** | 7 | Streams, rate limit, idempotency |
| Search | **Meilisearch 1.10** | 1.10+ | Typo-tolerant, fast |
| Storage | **Cloudflare R2** | n/a | Zero egress |
| CDN | **Cloudflare** | n/a | Edge cache + Workers |
| Auth | **Lucia** (or Supabase Auth) | 3.x | Session-based, no vendor lock |
| ML — separation | **Demucs v4 htdemucs_ft** + **Mel-Band-Roformer** | 4.0.1 / 2024 | SOTA SDR |
| ML — beats | **Beat-Transformer** | 2023 | SOTA downbeat F1 |
| ML — structure | **SA3** / All-in-One | 2024 | Coarse sections |
| ML — lyrics | **Whisper large-v3** + **WhisperX** | 2024 | SOTA WER, word-level |
| ML — translation | **NLLB-200-distilled-600M** | 2023 | 200+ langs |
| ML — pitch | **CREPE** or **pyin** | latest | Vocal pitch |
| ML serving | **PyTorch 2.5** + **TorchServe** (or BentoML, Ray Serve) | 2.5+ | Batching, autoscale |
| GPU | **NVIDIA L4** (cost-effective) or **A10** (faster) | n/a | Spot / on-demand mix |
| Container | Docker + Compose (dev), Kubernetes (prod) | n/a | Standard |
| Observability | **OpenTelemetry** → Grafana + Loki + Tempo | n/a | Traces / logs / metrics |
| CI | GitHub Actions + golden-set regression | n/a | Pre-merge model check |

---

## 8. Data Model (key tables)

```sql
-- users
users (
  id uuid PK,
  email text UNIQUE,
  password_hash text,
  role text CHECK (role IN ('guest','user','trusted','mod','admin')),
  created_at timestamptz,
  trust_score int DEFAULT 0,
  banned boolean DEFAULT false
)

-- songs
songs (
  id uuid PK,
  owner_user_id uuid FK users.id,
  title text,
  artist text,
  album text,
  genre text,                    -- 'bachata','salsa','merengue',...
  style text,                    -- 'romantic','urban','mambo',...
  duration_sec numeric,
  source_format text,
  source_url text,               -- R2 key
  uploaded_by uuid FK users.id,
  visibility text,               -- 'private','community','curated'
  moderation_status text,        -- 'pending','approved','rejected'
  bpm numeric,
  key_signature text,
  time_signature text,
  created_at timestamptz
)

-- analysis versions (immutable)
song_analyses (
  id uuid PK,
  song_id uuid FK songs.id,
  version int,
  model_set jsonb,               -- {separator: 'demucs_v4_ft+roformer', beats: 'beat_transformer_v2', ...}
  params jsonb,
  status text,                   -- 'queued','running','done','failed','low_confidence'
  confidence_overall numeric,
  result jsonb,                  -- the full analysis: stems, beats, sections, lyrics, curves
  created_at timestamptz,
  UNIQUE (song_id, version)
)

-- stems (one row per output stem)
song_stems (
  id uuid PK,
  song_id uuid FK songs.id,
  analysis_id uuid FK song_analyses.id,
  stem_kind text,                -- 'vocals','requinto','bongo','guira',...
  r2_key text,
  format text,
  loudness_lufs numeric,
  sdr_db numeric,                -- separation quality
  duration_sec numeric
)

-- sections (denormalized for fast query)
song_sections (
  id uuid PK,
  song_id uuid FK songs.id,
  analysis_id uuid FK song_analyses.id,
  start_sec numeric,
  end_sec numeric,
  section_type text,             -- 'intro','verse','coro','mambo','soneo','puente','outro','breakdown'
  confidence numeric,
  pattern_label text,            -- 'derecho','dile_que_no','enchufla',...
  danceability_score numeric
)

-- lyrics (per word, per language)
song_lyrics (
  id uuid PK,
  song_id uuid FK songs.id,
  analysis_id uuid FK song_analyses.id,
  language text,
  start_sec numeric,
  end_sec numeric,
  text text,
  translation text,
  phonetic_ipa text,
  vocal_type text                -- 'lead','backing','coro','soneo'
)

-- user activity (for trust scoring, library, playlists)
playlists (id, owner_id, name, is_public, created_at)
playlist_songs (playlist_id, song_id, position)
annotations (id, user_id, song_id, start_sec, end_sec, body, created_at)
moderation_log (id, mod_id, song_id, action, reason, created_at)
audit_log (id, actor_id, action, target, payload, created_at)
```

---

## 9. UX / Presentation — Concrete Improvements

### 8.1 Layout (rebuilt, not skinned)

- **Single screen, 3-zone layout**:
  - **Top**: song meta + section ribbon (colored chips: Intro / Verse / Coro / Mambo / Soneo / Outro). Ribbon scrolls horizontally with playback; the current section is centered and emphasized.
  - **Center**: the **gem grid** — 4–8 vertical lanes, one per stem. Horizontal axis = time aligned to the **8-count** (4 bars shown at 128 BPM by default; user can zoom). The 8-count bar is heavy; the 4-count bar is lighter; beats are subtle ticks. Gem **vertical position = pitch** (so you *see* the requinto melody line, bongó high-low alternation, bass drops).
  - **Bottom**: the **musicality strip** — stacked curves (energy, onset density, bass, vocal activity) with detected "hits" as little chevrons. Below that: lyrics (karaoke style), below that: transport + tools.
- **Right panel (collapsible)**: per-stem mixer (volume, mute, solo, pan), pattern coach suggestions, key + chord, BPM, version diff.
- **Bottom drawer (pull up)**: settings, model info, confidence report, "what is this chip?" legend.

### 8.2 Color & theme

- **Dark by default** (dancers in dim clubs). High-contrast accent per stem.
- **Color-blind safe palette** (Wong / Okabe-Ito). Stem color != section color != chord color.
- Stem colors: Vocals (magenta), Requinto (teal), Segunda (sky), Bass (orange), Bongó (lime), Güira (yellow), Clave (violet), Palmas (grey).
- Optional **light theme** with same hues, desaturated.

### 8.3 Interactivity

- **Hover a gem** → tooltip: instrument, exact time, MIDI pitch, loudness, confidence.
- **Click a section chip** → jump + play from there, with 1-bar count-in.
- **Click a word in lyrics** → jump to that word, highlight in the gem grid (vocal pitch line lights up).
- **Drag across the gem grid** → define a loop region.
- **Cmd/Ctrl + scroll** → zoom time axis.
- **Space** → play/pause (with a tiny haptic on mobile).
- **M** → mute vocals. **P** → just percussion. **B** → just bass. **G** → just güira.
- **1–8** keys → jump to that beat in the current bar.
- **Long-press a stem lane** → solo that stem.

### 8.4 Mobile-first

- One-thumb reachable play, mute, loop, A-B.
- Pinch-zoom gem grid.
- Landscape mode auto-rotates the gem grid to fill width; portrait stacks gem grid + musicality strip + lyrics as swipeable cards.
- Haptic feedback on the beat (configurable).
- iOS Lock Screen / Android Media controls via Media Session API.

### 8.5 Accessibility

- WCAG 2.2 AA.
- All controls keyboard-reachable.
- Captions for the lyrics (open / closed).
- Reduced motion mode (turns off gem glow, uses static colors only).
- Screen-reader labels for every interactive element.
- All confidence states announced.

### 8.6 Onboarding

- **30-second tour** (3 cards) instead of long pages.
- First song pre-loaded; user hears it the moment they land.
- Tooltips are contextual and dismissible.
- No modal popups.

---

## 10. Performance — How We Stay Fast

| Concern | Solution |
|---|---|
| Gem rendering at 60fps with 10k+ gems | Pixi.js v8 with batched container, GPU instancing for gem shape, cull off-screen bars |
| Initial load | PWA with route-level code splitting, audio assets lazy-loaded on first play, stem download only when user opens a stem mixer control |
| Stem file size | FLAC for download, Opus 96 kbps for streaming, waveform peaks pre-computed and JSON-cached |
| ML job queue | Dramatiq with rate limit, batch GPU inference, model warm pool |
| Search | Meilisearch with 50ms p99 |
| Memory | Lazy stem decode, release buffers on song change, IndexedDB caches for repeat plays |
| Network | HTTP/3, Brotli, Cloudflare cache for stems (immutable per analysis version) |
| Database | Read replicas for library reads, Redis for hot songs |
| Mobile battery | Pause WebGL when tab hidden, throttle to 30fps in low-power mode, optional "lite view" (gem grid only) |

### Performance budget targets
- **Time to interactive**: < 2.5 s on 4G
- **Largest Contentful Paint**: < 2.0 s
- **Gem grid 60fps** on iPhone 13 / Pixel 7 mid-song with 8 stems
- **Audio latency** (tap-to-mute): < 50 ms
- **Stem separation throughput**: 1× real-time on L4, 1.5× on A10, 3× on H100
- **End-to-end analysis** (upload → stems + analysis ready): < 3 min for a 4-min song

---

## 11. Free Feature Catalog (everything)

> Because there's no business model, **everything below is free for every user**. Roles only affect *visibility* and *moderation*, not access.

### Free for everyone (no login)
- Listen to all songs in the **Curated** and **Community** libraries
- Full visualization: gem grid, musicality curves, sections, lyrics
- 6–8 stem mute/solo + custom mix
- Loop region, speed 50–150%, pitch ±6
- Metronome (8th, 16th, martillo, clave)
- Lyrics + translation + phonetics
- Pattern coach suggestions (toggle off)
- Practice tools (A-B, count-in)
- Export stems (FLAC) for songs you own
- Export analysis as JSON / CSV
- Share song via deep link

### Free for **User** (logged in, default)
- **Upload your own songs** (unlimited, free, FLAC/WAV/MP3/M4A/OGG, up to 100 MB / 30 min each)
- Private library of your uploads
- Annotations (per-bar notes) on your own songs
- Build custom playlists
- Save stem mix presets
- Public profile (optional)
- "Request community publication" (subject to moderation)

### Free for **Trusted User** (auto)
- All of the above
- Publish to Community Library (subject to mod approval)

### Free for **Moderator**
- Moderation queue UI
- Approve / reject / hide / lock
- View audit log of own actions

### Free for **Admin**
- All of the above
- Curated library management
- Model version pinning, kill switches
- Role assignment
- Feature flags
- Global analytics dashboard
- Re-analyze any song with any model
- Edit metadata, fix transcription, override section labels
- Database admin tools (read-only by default; destructive ops require typed reason + secondary admin co-sign)

---

## 12. Reliability & Quality Gates

- **Golden test set** of 200+ hand-labelled bachata & salsa tracks.
  - 100 bachata (10 styles × 10 songs)
  - 100 salsa (10 styles × 10 songs)
  - Labels: BPM, 8-count phase, sections (intro/verse/coro/mambo/soneo/breakdown/outro), clave (2-3/3-2), vocals presence, instrumentation
- **CI gate**: every model upgrade must hit ≥ 98% BPM MAE < 1, ≥ 95% downbeat F1, ≥ 90% section-boundary F1, ≥ 90% stem SDR. Regressions > 2% block merge.
- **Shadow run** for new models: 7 days of parallel inference, compare diffs in admin dashboard, manual sample review.
- **Daily health check**: 5 random songs re-analyzed, SDR / WER / F1 logged. Anomaly alerts to admin.
- **User feedback loop**: "Was this section correct?" thumbs per section, fed into next model training.

---

## 13. Privacy & Open Source

- **Open source** (MIT or Apache 2.0) — code, model cards, golden test set, training data manifest.
- **No telemetry by default**. Opt-in only.
- **Audio never leaves your device for previews**; the heavy ML runs client-side when possible.
- **Uploaded songs are private by default.** Visibility is opt-in.
- **No third-party trackers**, no analytics SDK, no ads, no "marketing" cookies.
- **GDPR / CCPA / LGPD** compliant out of the box.
- **Right to be forgotten**: hard delete of all user rows, R2 objects, derived analyses.

---

## 14. Implementation Roadmap (12-week MVP → 6-month v1)

### Phase 0 — Foundations (week 0, 1 day)
- Repo setup, monorepo (pnpm + uv), CI, golden test set scaffold, Figma-style wireframe.

### Phase 1 — MVP (weeks 1–4)
- SvelteKit PWA, auth (User + Admin), user upload + admin upload, R2 storage.
- Demucs v4 stem separation, server-side only.
- Basic gem grid (4 stems: vocals, requinto, bass, drums).
- Beat-Transformer for BPM + downbeats.
- Lyrics: Whisper large-v3 + WhisperX, single translation (English).
- Section detection: SA3 + rule layer.
- iOS + Android installable PWA, basic accessibility.

### Phase 2 — Musicality (weeks 5–7)
- 6–8 stems including segunda, bongó, güira, clave.
- Roformer ensemble.
- Custom bachata 8-count validator + clave detector.
- Musicality curves (energy, density, flux, bass, vocal, hits, drops).
- Pitch-contour line for vocals.
- Pattern coach (rule-based, 80 patterns).
- Multi-language translation (NLLB, top 20 languages first).

### Phase 3 — Practice & Sharing (weeks 8–9)
- Loop region, speed, pitch shift, count-in, custom metronome.
- Stem mixer with presets.
- Export stems + analysis JSON/CSV.
- Shareable deep links with playback position.
- Library search (Meilisearch) with structured filters.

### Phase 4 — Roles & Moderation (week 10)
- Trusted-user auto-promotion, mod queue, admin dashboard, audit log, feature flags, model kill switch.

### Phase 5 — Polish (weeks 11–12)
- Accessibility audit (WCAG 2.2 AA).
- Performance budget enforcement.
- Onboarding tour.
- Cross-browser test (Safari, Firefox, Chrome, Edge, mobile).
- Open-source release prep: README, CONTRIBUTING, model cards, golden-set publishing.

### Phase 6 — Post-MVP (months 4–6)
- Real-time collaborative annotations (lightweight, optional).
- iOS / Android wrapper for App Store / Play Store (if desired for haptics + media controls parity).
- Salsa-specific deep features (clave first-class, montuno, soneo, call-and-response visualization).
- Pro-trainer mode: lets a dance teacher embed notes per section.
- Community pattern lexicon: let users tag patterns and share.
- Mobile client-side stem preview (ONNX Roformer-tiny).
- Light & dark themes, color-blind modes.

---

## 15. Success Metrics (technical & product)

| Metric | Target (6 months) |
|---|---|
| Stem SDR (golden set) | ≥ 9 dB vocals, ≥ 7 dB other stems |
| BPM MAE | < 0.5 BPM on 90% of golden |
| 8-count phase correctness | > 95% of bars correctly phased |
| Section boundary F1 | > 0.88 |
| Lyrics WER (Spanish bachata) | < 8% |
| Clave detection accuracy (salsa) | > 90% on golden |
| Time-to-interactive (PWA, 4G) | < 2.5 s |
| End-to-end analysis latency (4-min song) | < 3 min median |
| 60fps gem grid (iPhone 13, 8 stems) | 99th percentile |
| User-reported correct-section rate | > 85% |
| Monthly active users | n/a (we don't track; this is for the open community) |

---

## 16. Locked Decisions

| # | Decision | Locked value | Rationale |
|---|---|---|---|
| 1 | **Name** | **Compás** | Spanish for *beat / rhythm / compass*. Used everywhere |
| 2 | **Framework** | **SvelteKit 2 + Svelte 5** | Smaller bundle, better PWA, simpler reactivity fits the audio engine |
| 3 | **Hosting (now)** | **Local PC only** | No cloud, no R2 yet. SQLite + local filesystem. Everything runs on `localhost` |
| 3a | **Hosting (later)** | Cloudflare R2 + Workers | Phase 6 (post-MVP) when we have a public library + multi-user |
| 4 | **Genre scope** | **Bachata + Salsa only** (no merengue v1) | Locked §1 taxonomy is bachata + salsa; merengue needs its own stems + sections |
| 5 | **Mobile** | **Pure PWA** | No TWA / Capacitor for v1. Re-evaluate after core UX is locked |
| 6 | **Golden set** | **I draft the annotation guidelines** | See `ANNOTATION_GUIDELINES.md`. User reviews + annotates 5 pilot songs first, then we scale |
| 7 | **License** | **Apache 2.0** | Patent grant protects the ML pipeline |
| 8 | **Domain & repo** | **None yet** — runs on user's local PC | Defer until we have a public library to serve |

### Local-first dev environment (locked)
- **DB**: SQLite via `better-sqlite3` (zero install, single file, perfect for local dev). Schema is portable to Postgres later.
- **Cache / queue**: in-process for v0.1 (no Redis). Dramatiq can use a SQLite broker for dev.
- **Storage**: local filesystem under `apps/api/storage/` (originals, stems, analysis JSON).
- **Search**: SQLite FTS5 (good enough for the local library; upgrade to Meilisearch when public).
- **Frontend**: SvelteKit dev server on `localhost:5173`.
- **API**: FastAPI + uvicorn on `localhost:8000`.
- **Worker**: separate `python -m worker` process; same code as production.
- **ML**: client-side ONNX Runtime Web for preview stems; server-side Demucs/Roformer invoked as Python scripts (CPU works, just slower).

---

## 17. What I'll Do Next (Once You Say Go)

1. Lock the open decisions above.
2. Scaffold the monorepo: `apps/web` (SvelteKit), `apps/api` (FastAPI), `apps/worker` (Dramatiq), `packages/ml` (model runners), `packages/shared-types`, `infra/`.
3. Build the golden test set scaffold + a 5-song pilot to prove the pipeline.
4. Deliver a clickable prototype of the gem-grid view (Pixi.js) with a single song's analysis, so you can validate the visualization before we invest in the full ML pipeline.
5. Iterate.

Tell me which of the §15 decisions you want to lock and which to leave for me, and I'll start scaffolding immediately.
