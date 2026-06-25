# AGENTS.md

Instructions for AI coding agents working on this repository.

## Project overview

Monorepo for an LLM-powered code review pilot (**Nexo Co-Review**, codename `nexo-coreview`):

- **Agent** — Python 3.11+, MCP server (`coreview-agent`), OpenCode runtime image
- **Backend** — Python 3.11+, FastAPI, asyncpg, Celery, Typer CLI (`code-review`)
- **Frontend** — React 19, Vite, TanStack Router/Query/Table, shadcn/ui (New York)
- **Database** — PostgreSQL (dbmate migrations)
- **Agent runtime** — [OpenCode](https://opencode.ai/) + MCP toolbase (Git/CI tools)

Production ships as a single Docker image (API + bundled SPA). Architecture diagrams: `docs/architecture.svg`, `docs/flow.svg`.

### Runtime architecture

Three layers with clear boundaries:

1. **Backend (API)** — Configuration management, webhooks, frontend API. Stores repo integrations and LLM providers in Postgres.
2. **Job (Celery worker)** — Reads review + integration config from DB, builds a full `NEXO_COREVIEW_*` env dict, spawns a one-shot agent container via the Docker runtime provider.
3. **Agent (stateless container)** — Receives all execution config via env (materializes ephemeral `opencode.json` locally). Runs clone → LLM review → GitHub post. Reports progress and findings via **HTTP callback** (schema v1, HMAC-signed); it does **not** connect to Postgres.

The agent does **not** read `repo_integrations` or `llm_providers` from the database.

### Review callback (schema v1)

Agent posts `review.started`, `review.completed`, and `review.failed` events to `NEXO_COREVIEW_CALLBACK_URL` with `X-Review-Signature-256` HMAC auth. Spec: [`docs/review-callback-v1.schema.json`](docs/review-callback-v1.schema.json). Nexo backend receives them at `POST /api/v1/agent/review-events` and persists to Postgres. Third-party orchestrators can implement the same contract without Nexo schema.

### CLI modes

```bash
cd backend && uv run code-review backend run   # FastAPI server
cd backend && uv run code-review job worker    # Celery worker (prepare env + spawn agent)
cd agent && uv run coreview-agent review run --review-id <uuid>  # one-shot review (env injected by job)
```

### Provider abstractions

Protocols, GitHub Git/CI implementations, runtime specs (Docker/K8s), OpenCode LLM provider, and callback schemas live in **`shared/`** (`coreview-shared` package). Backend and agent wire them via local `factory.py` and app-specific config.

| Module (in `coreview_shared`) | Purpose |
|--------|---------|
| `llm/opencode` | OpenCode CLI review runner |
| `providers/git`, `providers/ci` | GitHub clone, diff, webhook, CI summary |
| `runtime/docker`, `runtime/k8s` | Job execution and workspace isolation |
| `schemas/review_callback` | Agent callback contract (v1) |

Backend-specific: `backend/app/providers/factory.py`, `opencode_config.py` (multi-provider DB merge). Agent-specific: `agent/app/providers/factory.py`, MCP toolbase in `agent/app/toolbase/`.

Agent skills bundled into the Docker image live in `agent/skills/` (OpenCode). IDE/dev skills remain in `.agents/skills/`. MCP tools are in `agent/app/toolbase/`.

## Prerequisites

- Docker Compose v2.22+ (`watch` support for file sync)
- [uv](https://docs.astral.sh/uv/) and Node.js 22+ only for host-side lint/test/openapi tasks
- Python deps are managed as a **uv workspace** (`pyproject.toml` + `uv.lock` at repo root). Run `uv lock` from the repo root after changing dependencies in `shared/`, `backend/`, or `agent/`.

## Setup commands

```bash
cp .env.example .env

# Docker dev (recommended): HMR + Uvicorn reload + Compose Watch
make dev-watch

# Or without watch:
make dev

# Production (base compose only, profile prod):
make prod-up
```

| URL | Service |
|-----|---------|
| http://localhost:5173 | Frontend (Vite HMR, dev only) |
| http://localhost:8000/docs | OpenAPI / Swagger |
| http://localhost:8000/api/v1/health | Health check |

On `make dev` / `make prod-up`, Compose automatically runs **dbmate migrate**, **render opencode config**, and **build agent image** before starting app services.

On Docker Desktop (macOS/Windows), set `CHOKIDAR_USEPOLLING=true` in `.env` if HMR misses file changes.

## Dev environment tips

- Root `.env` is loaded by Makefile, backend (`pydantic-settings`), and Compose.
- **Infrastructure env vars** use prefix `NEXO_COREVIEW_*` (Redis, Docker, OpenCode, MCP). See `.env.example`.
- **Dynamic settings** (repos, webhook secrets, GitHub tokens, LLM providers) are stored in Postgres and edited at `/settings` — do not hardcode secrets.
- After changing API routes or Pydantic schemas, run `make openapi` to refresh `openapi.json` and `frontend/src/api/generated/schema.ts`.
- After adding LLM providers via Settings, `opencode.generated.json` is regenerated; each new review spawns a fresh agent container with the latest config.
- Compose layout: `docker-compose.yaml` (base) + `docker-compose.override.yaml` (dev, auto-merged). Production uses only the base file: `make prod-up`.
- `routeTree.gen.ts` is generated by TanStack Router — do not hand-edit.

## Project structure

```
shared/                 # coreview-shared — protocols, providers, callback schemas (not a runtime service)
  coreview_shared/
backend/
  app/
    api/v1/           # Versioned HTTP routes
    repositories/     # asyncpg data access (dataclass rows)
    schemas/          # Pydantic request/response models
    services/         # Business logic
    providers/        # factory + OpenCode config merge (implementations in coreview_shared)
    jobs/             # Celery tasks
    cli/              # Typer commands
  migrations/         # dbmate SQL (-- migrate:up / migrate:down)
  tests/
agent/
  skills/             # OpenCode skills (bundled in agent image)
  app/
    mcp/              # MCP server (FastMCP)
    toolbase/         # Git/CI MCP tool handlers
    providers/        # factory wiring from env
    repositories/     # repo_integrations (per-repo credentials)
    cli/              # coreview-agent Typer CLI
  docker/             # entrypoint + default opencode config
  Dockerfile          # OpenCode + MCP + git image
  tests/
frontend/
  src/
    routes/           # TanStack Router file-based routes
    api/              # HTTP client + generated OpenAPI types
    hooks/            # TanStack Query hooks
    components/ui/    # shadcn components
.agents/skills/       # IDE/dev agent skills (shadcn, etc.)
```

## Adding a new API feature

1. Add SQL migration in `backend/migrations/` (dbmate format)
2. Add repository in `backend/app/repositories/`
3. Add Pydantic schemas in `backend/app/schemas/`
4. Add route in `backend/app/api/v1/` and register in `backend/app/api/router.py`
5. Add TanStack Query hook in `frontend/src/hooks/`
6. Add page under `frontend/src/routes/`
7. Run `make openapi` and `make lint`

## Code style

### Python (backend)

- Ruff: line length 88, target Python 3.11; rules `E`, `F`, `I`, `UP`
- Use `uv run` for all Python commands inside `backend/`
- Repositories return frozen `@dataclass` rows; services orchestrate logic
- Async throughout: asyncpg, httpx, FastAPI `async def` handlers
- Config via `app.config.Settings` and `CodeReviewSettings` (`NEXO_COREVIEW_` prefix)
- Import order enforced by Ruff (`I`)

### TypeScript (frontend)

- Strict TypeScript; path alias `@/` maps to `src/`
- React Compiler enabled (`babel-plugin-react-compiler`) — avoid manual `memo`/`useMemo` unless necessary
- Data fetching via TanStack Query hooks in `src/hooks/`, not ad-hoc `useEffect` + `fetch`
- API types from `src/api/generated/schema.ts` (generated — do not edit)
- shadcn/ui New York style; add components with the shadcn skill / CLI, not copy-paste from random sources
- ESLint flat config in `frontend/eslint.config.js`

### General

- Minimize scope: match existing patterns, no drive-by refactors
- Comments only for non-obvious business logic
- Do not commit `.env`, tokens, or generated secrets

## Testing instructions

```bash
make test-unit     # pytest, no database (integration tests skipped)
make test          # unit + integration (requires Postgres)
make lint          # ruff + ESLint + tsc
```

Run backend tests directly:

```bash
cd backend && uv run pytest                    # unit only
cd backend && uv run pytest -m integration     # integration only
cd backend && uv run pytest tests/api/test_reviews.py -k "webhook"
```

Integration tests need Postgres (`docker compose up -d db redis && make migrate`, or run the full dev stack with `make dev`).

Add or update tests for behavior you change. API tests use `httpx.AsyncClient` with mocked dependencies where appropriate.

## Security considerations

- Treat Server Actions / public API routes as untrusted: validate input, authenticate webhooks (GitHub HMAC)
- Webhook endpoint: `POST /api/v1/webhooks/github`
- Never log or commit `NEXO_COREVIEW_*` tokens, webhook secrets, or GitHub PATs
- Worker mounts Docker socket for isolated git workspaces — keep runtime images minimal (`alpine/git`)
- Dynamic credentials belong in Postgres (Settings UI), not in source code

## PR instructions

Before opening a PR:

1. `make lint` — must pass
2. `make test-unit` — must pass; run `make test` if you touched DB repositories or migrations
3. `make openapi` — if API contracts changed
4. Apply migrations locally and verify `make migrate` succeeds

Commit messages: concise, imperative mood, focus on *why* (e.g. `fix webhook signature check for repo integrations`).

Title format: short summary of the change (no strict prefix required).

## Useful commands reference

| Command | Description |
|---------|-------------|
| `make dev` | Docker dev stack (`docker compose up --build`) |
| `make dev-watch` | Docker dev with Compose Watch |
| `make dev-down` / `make down` | Stop stack |
| `make prod-up` / `make up` | Production stack (profile `prod`) |
| `make migrate` / `make migrate-down` | dbmate up / down via Compose |
| `make render-opencode-config` | Regenerate `opencode.generated.json` via Compose |
| `make build-agent` | Build agent image via Compose |
| `make openapi` | Export OpenAPI + regenerate TS types (host) |
