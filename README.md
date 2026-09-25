# Compás

> Open, free musical companion for **salsa & bachata** dancers (and musicians).
> Apache 2.0. No paywalls. No business model. Real ML analysis, runs on your PC.

---

## What it does

Compás takes a **bachata or salsa song** and tells you exactly what's happening, beat by beat, instrument by instrument:

- **Splits the song into stems** (vocals, requinto/segunda, bass, bongó, güira, drums, etc.) using **Demucs v4** (htdemucs, the SOTA open-source separator)
- **Detects BPM and the 8-count** with `librosa` (or `essentia` if you prefer)
- **Detects song sections** (intro / verso / coro / mambo / majae / soneo / breakdown / …) using a rule-based classifier on per-stem features
- **Detects clave direction** (2-3 vs 3-2) for salsa via drum-onset correlation
- **Maps every instrument onset to a gem** on a time-aligned grid, with **pitch-aware vertical positioning** — you literally *see* the requinto melody
- **Renders 4 musicality curves** (energy, onset density, bass RMS, vocal activity) under the grid so you can *feel* when the music opens up vs when it's telling a story
- **(Optional)** Transcribes lyrics with **Whisper** + per-word timestamps

The visualization is a single-page web app that streams the original audio, plays the song, lets you **loop A-B regions**, **change speed without changing pitch**, and **mute/solo individual stems**.

---

## Quick start (your PC)

### Prerequisites
- **Node.js 20+**
- **pnpm 9+** (`npm install -g pnpm`)
- **Python 3.11+**
- **uv** (Python package manager — `pip install uv` or `brew install uv`)
- **ffmpeg + ffprobe** (`brew install ffmpeg` / `apt install ffmpeg`)

### One-time install
```bash
git clone https://github.com/christianchavezmoya-bot/Comp-s-.git compas
cd compas
pnpm install

# Python deps (torch, demucs, librosa, fastapi, sqlalchemy, etc.)
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install "demucs>=4.0.1" "librosa>=0.10" "soundfile" "numpy<2" "scipy<1.14" "torch==2.1.0" "torchaudio==2.1.0" \
                 "fastapi" "uvicorn[standard]" "sqlalchemy" "aiosqlite" "pydantic[email]" "email-validator" \
                 "python-multipart" "pydantic-settings" "httpx" "essentia" "openai-whisper"
```

### Run dev servers (3 terminals)
```bash
# Terminal 1 — API on http://localhost:8000
cd compas/apps/api
../../.venv/bin/uvicorn compas_api.main:app --reload --port 8000

# Terminal 2 — Web on http://localhost:5173
cd compas
pnpm --filter @compas/web run dev

# Terminal 3 (optional) — Worker (no-op in v0.2)
cd compas/apps/worker
../../.venv/bin/python -m compas_worker.main
```

### Use it
1. Open **http://localhost:5173**
2. Click **+ Upload** in the sidebar; pick a `.flac`/`.wav`/`.mp3` bachata or salsa file
3. Click **▶ Analyze** — first analysis takes ~3 min for a 3-min song on CPU
4. Once done, the **gem grid** appears: diamonds for every instrument onset, colored by stem
5. Use the transport controls: **play/pause**, **seek bar**, **loop A-B**, **speed 0.5×–1.5×** (with pitch preserved)
6. Click any **section chip** to jump to it
7. Use the **stem mixer** below the grid to mute/solo individual instruments

---

## What works (v0.2 — production-shape)

| Layer | Status | Notes |
|---|---|---|
| **Stem separation (Demucs v4 htdemucs)** | ✅ | 4 stems: vocals, drums, bass, other. CPU: ~3× real-time |
| **BPM / beats / downbeats (librosa)** | ✅ | With half/double-time correction. Optional `essentia` backend |
| **8-count validation** | ✅ | Scores phase candidates against requinto onsets |
| **Section detection** | ✅ | 10-section taxonomy for bachata, 8+4 for salsa. Rule-based |
| **Clave direction (salsa)** | ✅ | 2-3 vs 3-2 with confidence + mid-song switches |
| **Onset detection per stem** | ✅ | librosa onset + spectral centroid → pitch MIDI |
| **Gem grid visualization (Pixi.js v8)** | ✅ | 60fps, pitch-aware gems, section ribbons, musicality curves, loop markers, click-to-seek |
| **Audio streaming (HTTP range)** | ✅ | Original + per-stem FLAC |
| **Lyrics (Whisper)** | ✅ | Off by default (slow). Set `COMPAS_TRANSCRIBE=true` to enable |
| **Library CRUD** | ✅ | List, get, upload, delete |
| **Auth + roles** | ✅ | Email/password, PBKDF2 hashing, signed session cookies |
| **User + Admin upload** | ✅ | Both can upload, both can analyze |
| **Versioned analyses** | ✅ | Every model upgrade creates a new immutable version |
| **SQLite (dev) / Postgres-portable schema** | ✅ | SQLAlchemy, same SQL works on either |
| **Local PWA-friendly web app** | ✅ | SvelteKit 2 + Svelte 5 + Vite 5 + Tailwind-ready |

## What doesn't (yet)

- **GPU acceleration** — CPU only for now. Set `device=cuda` in `compas_ml/config.py` to use a GPU
- **htdemucs_ft** (finer separator) — opt-in via `COMPAS_USE_HTDEMUCS_FT=true` env. ~5× slower
- **WhisperX word-level timestamps** — we use `openai-whisper` segment-level timestamps. WhisperX integration is the next upgrade
- **Salsa per-stem finer split** (piano, congas, timbales, cowbell separated) — Demucs gives 4 stems, finer split via classifier is in design
- **Lyrics translation** (NLLB-200) — pipeline stub is there, not yet wired
- **Pattern coach** (move suggestions) — UI not yet built
- **Mobile PWA optimizations** (offline cache, haptics) — basic only
- **Production deployment** — local-only; Cloudflare R2 / Workers config is in the plan but not deployed
- **Golden test set** — sample annotation only, no full 200-song set yet

---

## Repo layout

```
compas/
├── apps/
│   ├── web/                    SvelteKit 2 + Pixi.js v8 + Tone.js
│   │   ├── src/lib/
│   │   │   ├── GemGrid.svelte  the visualization
│   │   │   └── api.ts          the API client
│   │   └── src/routes/+page.svelte
│   ├── api/                    FastAPI + SQLite
│   │   └── compas_api/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── db.py
│   │       └── routers/
│   │           ├── auth.py
│   │           ├── library.py
│   │           ├── analysis.py
│   │           └── health.py
│   └── worker/                 Dramatiq stub (Phase 4+)
├── packages/
│   ├── shared-types/           TypeScript types (used by web + future mobile)
│   └── ml/                     Python ML pipeline
│       └── compas_ml/
│           ├── config.py
│           ├── io_utils.py
│           ├── separation.py   Demucs wrapper
│           ├── beats.py        librosa + essentia
│           ├── onsets.py
│           ├── sections.py     rule-based
│           ├── clave.py        salsa 2-3 vs 3-2
│           ├── lyrics.py       Whisper
│           └── pipeline.py     orchestrator
├── golden/                     annotation tooling
│   ├── songs/
│   ├── sources/
│   └── scripts/{intake,validate,stats}.py
├── storage/                    runtime data (gitignored)
│   ├── compas.db
│   ├── originals/<song_id>/source.flac
│   └── analysis/<song_id>/{stems/, analysis.json}
├── COMPAS_PLAN.md              full plan + locked decisions
├── LICENSE                      Apache 2.0
└── README.md                   you are here
```

---

## API quick reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | health check |
| `POST` | `/api/auth/register` | create user (role: `user` or `admin`) |
| `POST` | `/api/auth/login` | session cookie |
| `POST` | `/api/auth/logout` | clear cookie |
| `GET` | `/api/auth/me` | current user (or null) |
| `GET` | `/api/library/songs?genre=bachata` | list songs |
| `POST` | `/api/library/songs` | upload a song (multipart: `title`, `artist`, `genre`, `audio`) |
| `GET` | `/api/library/songs/{id}` | get one song |
| `DELETE` | `/api/library/songs/{id}` | delete a song |
| `GET` | `/api/library/songs/{id}/audio` | stream the original (HTTP range supported) |
| `GET` | `/api/library/songs/{id}/stems/{stem}` | stream a stem FLAC |
| `POST` | `/api/analysis/songs/{id}/analyze` | run the full pipeline (synchronous by default) |
| `GET` | `/api/analysis/songs/{id}/latest` | get the latest analysis JSON |
| `GET` | `/api/analysis/songs/{id}/status` | just the status |

OpenAPI/Swagger UI: **http://localhost:8000/docs**

---

## Env vars

| Var | Default | What it does |
|---|---|---|
| `COMPAS_RUN_ML_INLINE` | `true` | If true, `/analyze` blocks until done. If false, queues in background |
| `COMPAS_USE_HTDEMUCS_FT` | `false` | Use the higher-quality htdemucs_ft separator (~5× slower) |
| `COMPAS_TRANSCRIBE` | `false` | Run Whisper on the vocal stem (adds significant time) |
| `COMPAS_MAX_UPLOAD_MB` | `100` | Max upload size in MB |
| `COMPAS_DB_PATH` | `<project>/storage/compas.db` | SQLite location |
| `COMPAS_STORAGE_DIR` | `<project>/storage` | Audio + stems location |
| `COMPAS_SESSION_SECRET` | `dev-secret-change-me` | Session signing key. **Set this in production** |
| `TORCH_HOME` | `~/.cache/torch` | PyTorch model cache |
| `DEMUCS_CACHE` | `~/.cache/demucs` | Demucs model cache |

---

## License

Apache 2.0. See [`LICENSE`](./LICENSE).
