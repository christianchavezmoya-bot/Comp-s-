# Compás

> Open, free musical companion for **salsa & bachata** dancers (and musicians).
> Apache 2.0. No paywalls. No business model. Built on a local PC first; cloud later.

---

## What is this?

Compás is a spiritual successor to **Dentro** — a web app that splits a salsa or bachata song into its instruments, maps the onsets to the 8-count, detects sections (intro / verso / coro / mambo / majae / soneo / breakdown / …), shows you which instrument cues which dance move, and overlays translated lyrics. The full vision is in [`COMPAS_PLAN.md`](./COMPAS_PLAN.md). The locked instrument and section taxonomy is in [`COMPAS_PLAN.md` §1](./COMPAS_PLAN.md#1-locked-genre-specification--instruments-sections-dance-mapping).

**Status**: v0.1 prototype. Working SvelteKit + Pixi.js gem-grid with mock data. Real ML pipeline lands in Phase 1.

---

## Repo layout (monorepo)

```
compas/
├── apps/
│   ├── web/                SvelteKit 2 + Svelte 5 + Pixi.js v8 + Tone.js
│   ├── api/                FastAPI + SQLite (local-first, Postgres-portable)
│   └── worker/             Dramatiq ML worker (stub for v0.1)
├── packages/
│   ├── shared-types/       TypeScript types shared by web + future mobile
│   └── ml/                 Python ML package: Demucs, Roformer, Beat-Transformer, Whisper
├── golden/                 The annotation test set (200 songs, hand-labeled)
│   ├── songs/              <uuid>.flac + <uuid>.json pairs
│   ├── sources/            drop new audio here, then run intake.py
│   └── scripts/            intake.py, validate.py, stats.py
├── infra/                  Deployment configs (cloud later)
├── docs/                   Additional docs
├── COMPAS_PLAN.md          The full project plan
├── ANNOTATION_GUIDELINES.md  How to hand-annotate the golden set
└── README.md               You are here
```

---

## Local setup (your PC)

### 0. Prerequisites
- **Node.js 20+** (tested with 22) — https://nodejs.org
- **pnpm 9+** (we pin 12.6) — `npm install -g pnpm` (or `corepack enable && corepack prepare pnpm@12.6.0 --activate`)
- **Python 3.11+** — https://python.org
- **uv** (Python package manager) — `pip install uv` or `brew install uv`
- **ffmpeg + ffprobe** (for audio duration probing) — `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
- *(optional)* **Docker** — only needed if you want Postgres instead of SQLite later

### 1. Clone & install
```bash
git clone <your-fork-url> compas
cd compas
pnpm install                          # installs JS deps across the monorepo
cd apps/api && uv sync                # installs Python deps for the API
cd ../worker && uv sync               # installs Python deps for the worker
cd ../..
```

### 2. Run dev servers (3 terminals, or use the runner)

**Terminal 1 — API** (port 8000):
```bash
cd compas/apps/api
uv run uvicorn compas_api.main:app --reload --port 8000
```

**Terminal 2 — Web** (port 5173):
```bash
cd compas
pnpm dev:web
```

**Terminal 3 — Worker** (no-op in v0.1; needed Phase 4+):
```bash
cd compas/apps/worker
uv run python -m compas_worker.main
```

**Or run them all in one go** (if you have `concurrently`):
```bash
cd compas
pnpm dev   # uses the workspace dev script
```

### 3. Open the app
Visit **http://localhost:5173** — you'll see the gem-grid prototype running with mock data.

### 4. Try the API
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"compas-api","version":"0.1.0"}

# Upload a song
curl -X POST http://localhost:8000/api/library/songs \
  -F "title=Obsesión" \
  -F "artist=Aventura" \
  -F "genre=bachata" \
  -F "audio=@/path/to/song.flac"

# List songs
curl http://localhost:8000/api/library/songs
```

API docs at **http://localhost:8000/docs** (auto-generated Swagger UI).

---

## Annotation workflow (the golden test set)

See [`ANNOTATION_GUIDELINES.md`](./ANNOTATION_GUIDELINES.md) for the full guide.

TL;DR:
```bash
# 1. Drop a song into sources/
cp /path/to/song.flac golden/sources/

# 2. Run intake to generate UUID + skeleton
python golden/scripts/intake.py golden/sources/song.flac

# 3. Open the generated .json in your editor and fill in:
#    - metadata (title, artist, genre, language)
#    - global.bpm (use BPM Tap or Mixed In Key as starting point)
#    - sections (use Sonic Visualiser)
#    - lyrics (transcribe what you hear)
#    - clave_segments (salsa only)
#    - hits, stems_present, stems_quality, etc.

# 4. Validate before committing
python golden/scripts/validate.py golden/songs/<uuid>.json

# 5. See coverage progress
python golden/scripts/stats.py
```

**Start with 5 pilot songs** (per §6 of the guidelines):
- Obsesión — Aventura (bachata moderna)
- Propuesta Indecente — Romeo Santos (bachata moderna)
- Darte un Beso — Prince Royce (bachata moderna)
- Vivir Mi Vida — Marc Anthony (salsa)
- Idilio — Willie Colón / Héctor Lavoe (salsa dura)

---

## Development phases

From the plan (§14):

| Phase | Weeks | What |
|---|---|---|
| **0** | 0–1 | Repo + golden set scaffold + this README |
| **1** | 1–4 | MVP: SvelteKit + FastAPI + Demucs stem separation + basic gem grid + BPM + simple lyrics |
| **2** | 5–7 | 7 (bachata) / 9–10 (salsa) stems, 8-count validator, clave detector, musicality curves, pattern coach |
| **3** | 8–9 | Practice tools, stem mixer, exports, shareable links |
| **4** | 10 | Roles, moderation, admin dashboard |
| **5** | 11–12 | Polish, a11y, performance, open-source release |
| **6** | 4–6 mo | Salsa-specific deep features, mobile wrappers, community pattern lexicon |

---

## Locked decisions

| | |
|---|---|
| Name | **Compás** |
| Genre scope | **Bachata + Salsa** (no merengue v1) |
| Framework | **SvelteKit 2 + Svelte 5** |
| Mobile | **Pure PWA** (no TWA / Capacitor v1) |
| License | **Apache 2.0** |
| Hosting (now) | **Local PC only** — SQLite + filesystem |
| Hosting (later) | Cloudflare R2 + Workers |

---

## Tech stack (locked)

| Layer | Tech |
|---|---|
| Frontend | SvelteKit 2 · Svelte 5 · Vite 5 · Tailwind v4 |
| Visualization | Pixi.js v8 (WebGL2) · Tone.js (audio scheduling) |
| Audio (client) | Web Audio API · ONNX Runtime Web (preview stems) |
| Backend | FastAPI · SQLAlchemy · better-sqlite3 (dev) → Postgres (prod) |
| ML | Demucs v4 htdemucs_ft · Mel-Band-Roformer · Beat-Transformer · Whisper large-v3 · WhisperX · NLLB-200 · librosa · essentia |
| Worker | Dramatiq + Redis (Phase 4+) |
| Storage | Local FS (dev) → Cloudflare R2 (prod) |
| Search | SQLite FTS5 (dev) → Meilisearch (prod) |
| Tests | pytest · Playwright (web) · vitest (components) |

---

## Contributing

1. Read [`COMPAS_PLAN.md`](./COMPAS_PLAN.md) — the architecture and decisions are all there.
2. Read [`ANNOTATION_GUIDELINES.md`](./ANNOTATION_GUIDELINES.md) — if annotating.
3. Open an issue before big changes so we can discuss.
4. PRs welcome. Apache 2.0.

---

## License

Apache License 2.0. See [`LICENSE`](./LICENSE) (TBD — to be added before public release).
