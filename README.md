# Code Review

Monorepo: **FastAPI + asyncpg** backend, **React + shadcn + TanStack** frontend, **PostgreSQL** database. Production ships as a single Docker image (API + bundled SPA).

## Prerequisites

- Python 3.11+, [uv](https://docs.astral.sh/uv/) (native dev only)
- Node.js 22+, Yarn (native dev only)
- Docker Compose v2.22+ (for `watch` support)

## Quick start — Docker dev (recommended)

Full stack with **Vite HMR**, **Uvicorn `--reload`**, and **Docker Compose Watch**:

```bash
cp .env.example .env

# First time: run migrations inside the compose network
make dev-migrate

# Start with file watching (rebuild on lockfile changes, sync source)
make dev-watch
```

Or without watch:

```bash
make dev
```

- Frontend (HMR): http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

`make dev-watch` merges [`docker-compose.yaml`](docker-compose.yaml) with [`docker-compose.override.yaml`](docker-compose.override.yaml) (loaded automatically per [Compose merge docs](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)). Bind mounts enable instant reload; `develop.watch` rebuilds images when `uv.lock` or `yarn.lock` change.

If HMR does not pick up file changes on Docker Desktop (macOS/Windows), set `CHOKIDAR_USEPOLLING=true` in `.env`.

## Quick start — native local development

```bash
cp .env.example .env

# 1. Start Postgres
make dev-db

# 2. Run migrations
make migrate

# 3. Backend (terminal 1)
make dev-api

# 4. Frontend (terminal 2)
make dev-web
```

## Production

```bash
make prod-up   # docker compose -f docker-compose.yaml --profile prod up -d
```

Production uses only the base compose file (`-f docker-compose.yaml`), so `docker-compose.override.yaml` is **not** merged.

## Compose file layout

| File | Purpose |
|------|---------|
| [`docker-compose.yaml`](docker-compose.yaml) | Base: `db`, `app` (profile `prod`), `migrate` (profile `tools`) |
| [`docker-compose.override.yaml`](docker-compose.override.yaml) | Dev: `api` (Uvicorn reload), `web` (Vite HMR), Compose Watch |
| [`dev.Dockerfile`](dev.Dockerfile) | Multi-stage dev images (`target: api` / `target: web`) |
| [`Dockerfile`](Dockerfile) | Production bundle (API + static SPA) |

## Common commands

| Command | Description |
|---------|-------------|
| `make dev-watch` | Docker dev stack with Compose Watch (HMR + reload) |
| `make dev` | Docker dev stack without watch |
| `make dev-down` | Stop Docker dev stack |
| `make dev-migrate` | Run migrations in compose network |
| `make dev-db` | Start Postgres only |
| `make dev-api` | Uvicorn with reload (native) |
| `make dev-web` | Vite dev server (native) |
| `make dev-worker` | Celery worker (native) |
| `make dev-opencode-serve` | Start OpenCode HTTP server (Docker) |
| `make render-opencode-config` | Generate `opencode.generated.json` from `NEXO_COREVIEW_LLM_*` |
| `make migrate` | Apply SQL migrations (dbmate) |
| `make openapi` | Export OpenAPI schema and generate TS types |
| `make lint` | Ruff + ESLint + typecheck |
| `make test-unit` | Unit tests (no database) |
| `make test` | Unit + integration tests (requires DB) |

## Project structure

```
backend/
  app/              # FastAPI application package
    api/v1/         # Versioned routes
    repositories/   # asyncpg SQL access
    schemas/        # Pydantic models
  migrations/       # dbmate SQL migrations
frontend/
  src/
    routes/         # TanStack Router file routes
    api/            # HTTP client + generated OpenAPI types
    components/ui/  # shadcn components
    hooks/          # TanStack Query hooks
```

## Adding a new feature

1. Add SQL migration in `backend/migrations/`
2. Create repository in `backend/app/repositories/`
3. Add Pydantic schemas in `backend/app/schemas/`
4. Add route in `backend/app/api/v1/`
5. Register router in `backend/app/api/router.py`
6. Add TanStack Query hook in `frontend/src/hooks/`
7. Add page in `frontend/src/routes/`
8. Run `make openapi` to refresh TypeScript types

## Environment variables

See [.env.example](.env.example). Key variables:

- `DATABASE_URL` — Postgres connection string
- `VITE_API_URL` — Frontend API base (default `/api/v1`)
- `VITE_API_PROXY_TARGET` — Vite proxy target (`http://api:8000` in Docker dev)
- `CHOKIDAR_USEPOLLING` — Enable polling file watcher in Vite (Docker Desktop)
- `APP_PORT` — Backend port (default `8000`)
- `WEB_PORT` — Frontend dev port (default `5173`)

### Code Review pilot (`NEXO_COREVIEW_*`)

Infrastructure env vars only (see [.env.example](.env.example)):

- `NEXO_COREVIEW_CELERY_BROKER_URL` — Redis broker URL
- `NEXO_COREVIEW_OPENCODE_SERVER_URL` — OpenCode `serve` base URL
- `NEXO_COREVIEW_OPENCODE_CONFIG_PATH` — Path to generated OpenCode config file

**Dynamic settings** (GitHub repo, webhook secret, GitHub token, LLM provider) are stored in Postgres and edited at **Settings** (`/settings` in the UI, `GET/PUT /api/v1/settings/integration`). Saving settings regenerates `opencode.generated.json`; restart `opencode-serve` to apply LLM changes.

**GitHub webhook:** `POST /api/v1/webhooks/github` (Pull request events: opened, synchronize, reopened).

**CLI modes:** `code-review backend run`, `code-review job worker`, `code-review agent run --review-id <uuid>`.
