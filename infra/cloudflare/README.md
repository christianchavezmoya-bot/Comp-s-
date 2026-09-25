# Compás — Cloudflare deployment

This directory contains the production deployment configs.

## Components

- **API** (FastAPI) → Cloudflare Worker (Python via `python_compat`)
- **Web** (SvelteKit) → Cloudflare Pages
- **Storage** (audio + stems) → Cloudflare R2 (zero egress)
- **ML worker** (Demucs/Roformer) → A separate VM with GPU (e.g. RunPod, Lambda, Hetzner)
- **Database** (Postgres) → Cloudflare Hyperdrive + Neon or Supabase
- **Search** (Meilisearch) → Meilisearch Cloud (free tier OK) or self-hosted

## One-time setup

### 1. R2 bucket

```bash
wrangler r2 bucket create compas-storage
wrangler r2 bucket create compas-storage-preview
```

### 2. Hyperdrive (Postgres)

```bash
# Create a Postgres database (e.g. on Neon: https://neon.tech)
# Then in Cloudflare dashboard: Workers → Hyperdrive → Create
# Copy the Hyperdrive ID into wrangler.toml
```

### 3. Secrets

```bash
wrangler secret put COMPAS_SESSION_SECRET
wrangler secret put DATABASE_URL
wrangler secret put MEILISEARCH_HOST
wrangler secret put MEILISEARCH_API_KEY
```

### 4. Web (Pages)

```bash
cd apps/web
pnpm add -D @sveltejs/adapter-cloudflare
# Change adapter-auto to adapter-cloudflare in svelte.config.js
pnpm build
wrangler pages deploy .svelte-kit/cloudflare --project-name=compas-web
```

### 5. API (Workers)

```bash
cd infra/cloudflare
wrangler deploy
```

## Local dev (this is what we use today)

The `apps/api` runs locally on `localhost:8000` with SQLite + filesystem. The web runs on `localhost:5173` via Vite. The dev server proxies `/api/*` to the local API.

## ML worker (separate service)

Demucs + Roformer are heavy. Run them on a GPU VM, not on Workers.

```bash
# On a GPU VM (Lambda, RunPod, Hetzner with GPU):
git clone https://github.com/christianchavezmoya-bot/Comp-s-.git
cd Comp-s-/apps/worker
uv venv .venv && source .venv/bin/activate
uv pip install -e .
# Run a Dramatiq worker that consumes from a Redis queue
dramatiq compas_worker.actors --processes 1 --threads 2
```

The worker reads jobs from the queue, runs the pipeline, uploads stems to R2, and writes the analysis JSON to Postgres.

## Costs (rough)

- **R2**: 10 GB free / month, then $0.015/GB. Stems for 1000 songs ≈ 50 GB = $0.60/month
- **Workers**: 100k requests/day free
- **Pages**: free for static sites
- **Hyperdrive**: free up to 1000 queries/day
- **GPU worker** (RunPod A10G spot): ~$0.40/hour, ~3 min/song = $0.02/song
- **Postgres (Neon free)**: 0.5 GB free
- **Meilisearch Cloud**: free tier covers hobby use

**Bottom line: under $50/month for thousands of users.**

## Migration path from local

1. Provision the services above
2. Set env vars
3. `wrangler deploy` (API) + `wrangler pages deploy` (Web)
4. Point a custom domain at both
5. Optional: enable Cloudflare Access for admin auth

The same code, just new env vars.
