# Contributing

Thanks for helping improve Nexo Co-Review. This guide covers local development, configuration, and the conventions we follow.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, asyncpg, Celery, Typer (`code-review` CLI) |
| Frontend | React 19, Vite, TanStack Router/Query/Table, shadcn/ui |
| Database | PostgreSQL (dbmate migrations) |
| Agent | [OpenCode](https://opencode.ai/) + MCP toolbase (Git/CI) |

Production ships as a single Docker image (API + bundled SPA).

## Prerequisites

- Docker Compose v2.22+ (`watch` support for file sync)
- [uv](https://docs.astral.sh/uv/) and Node.js 22+ for host-side lint, test, and OpenAPI generation

## Getting started

### Docker dev (recommended)

Full stack with Vite HMR, Uvicorn `--reload`, and Docker Compose Watch. Migrations, OpenCode config, and agent image build run automatically on startup.

```bash
cp .env.example .env
make dev-watch
```

Without watch:

```bash
make dev
```

| URL | Service |
|-----|---------|
| http://localhost:5173 | Frontend (HMR) |
| http://localhost:8000/docs | OpenAPI / Swagger |
| http://localhost:8000/api/v1/health | Health check |

`make dev-watch` merges [`docker-compose.yaml`](docker-compose.yaml) with [`docker-compose.override.yaml`](docker-compose.override.yaml). Bind mounts enable instant reload; `develop.watch` rebuilds images when root `uv.lock` or `yarn.lock` change. After changing Python dependencies in `shared/`, `backend/`, or `agent/`, run `uv lock` from the repo root.

On Docker Desktop (macOS/Windows), set `CHOKIDAR_USEPOLLING=true` in `.env` if HMR misses file changes.

### Production

```bash
cp .env.example .env
make prod-up   # docker compose -f docker-compose.yaml --profile prod up --build -d --wait
```

Production uses only the base compose file; `docker-compose.override.yaml` is not merged. Init jobs (migrate, opencode config, agent image) run automatically before `app` and `worker` start.

## Compose layout

| File | Purpose |
|------|---------|
| [`docker-compose.yaml`](docker-compose.yaml) | Base: `db`, `redis`, init jobs (`migrate`, `render-opencode`, `agent-image`), `app`/`worker` (profile `prod`) |
| [`docker-compose.override.yaml`](docker-compose.override.yaml) | Dev: `api`, `web`, `worker`, Compose Watch |
| [`dev.Dockerfile`](dev.Dockerfile) | Multi-stage dev images (`target: api` / `target: web`) |
| [`Dockerfile`](Dockerfile) | Production bundle (API + static SPA) |

Docker dev stack services: `api`, `worker`, `redis`, `db`. The worker mounts `/var/run/docker.sock`, loads review config from Postgres, injects `NEXO_COREVIEW_*` env vars, and spawns a per-review agent container built locally as `code-review-agent:dev` (`agent-image` service, `pull_policy: never` — no registry pull).

## Review execution flow

1. Webhook or retry enqueues `review.run` with a `review_id`.
2. Celery worker calls `prepare_review_job` ([`backend/app/services/review_job_prepare.py`](backend/app/services/review_job_prepare.py)) to resolve repo integration + LLM provider and build the agent env dict.
3. Docker runtime starts `coreview-agent review run --review-id <uuid>` with that env.
4. Agent materializes OpenCode config from env, executes the review, and POSTs lifecycle events + findings to the callback URL (`NEXO_COREVIEW_CALLBACK_*`). The API persists them via `POST /api/v1/agent/review-events`.

`opencode.generated.json` is still regenerated at a fixed path (repo root on host, `/config/opencode.generated.json` in Compose) for the Settings UI and API startup sync; agent containers build ephemeral config from injected env instead.

## Environment variables

Copy [`.env.example`](.env.example) to `.env`. The Makefile, backend (`pydantic-settings`), and Compose all read it.

### Application

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string |
| `VITE_API_URL` | Frontend API base (default `/api/v1`) |
| `VITE_API_PROXY_TARGET` | Vite proxy target (`http://api:8000` in Docker dev) |
| `CHOKIDAR_USEPOLLING` | Polling file watcher for Vite on Docker Desktop |
| `APP_PORT` | Backend port (default `8000`) |
| `WEB_PORT` | Frontend dev port (default `5173`) |

### Infrastructure (`NEXO_COREVIEW_*`)

These are infrastructure-only. Repo credentials and LLM profiles are stored in Postgres (Settings UI).

| Variable | Description |
|----------|-------------|
| `NEXO_COREVIEW_CELERY_BROKER_URL` | Redis broker URL |
| `NEXO_COREVIEW_DOCKER_HOST` | Docker Engine URL; empty = auto-detect per platform |
| `NEXO_COREVIEW_GIT_IMAGE` | Minimal git image (default `alpine/git:latest`) |
| `NEXO_COREVIEW_AGENT_CALLBACK_URL` | URL agent containers POST review events to (Compose: `http://api:8000/api/v1/agent/review-events`) |
| `NEXO_COREVIEW_AGENT_CALLBACK_SECRET` | Shared HMAC secret for callback auth |
| `NEXO_COREVIEW_MCP_SERVER_URL` | MCP SSE URL (default `http://mcp-serve:8001/sse`) |
| `MCP_PORT` | Host port for MCP server (default `8001`) |

GitHub tokens, webhook secrets, and LLM provider credentials are **not** infrastructure env vars — configure them in Postgres via **Settings** (`/settings`).

### Dynamic settings (database)

Configured via **Settings** (`/settings`) or the API:

- **LLM providers** — `GET/POST /api/v1/settings/llm-providers`, `PUT/DELETE .../{id}`
- **Repositories** — `GET/POST /api/v1/settings/repos`, `PUT/DELETE .../{id}`

Saving LLM providers regenerates `opencode.generated.json` for the backend; the job worker injects per-review LLM credentials into agent containers via env at spawn time.

## CLI modes

```bash
cd backend && uv run code-review backend run
cd backend && uv run code-review job worker
cd agent && uv run coreview-agent review run --review-id <uuid>
cd agent && uv run coreview-agent serve --transport sse --host 0.0.0.0 --port 8001
```

## Project structure

```
backend/
  app/
    api/v1/           # Versioned HTTP routes
    repositories/     # asyncpg data access (dataclass rows)
    schemas/          # Pydantic models
    services/         # Business logic
    providers/        # Swappable LLM, Git, CI, runtime adapters
    jobs/             # Celery tasks
    cli/              # Typer commands
  migrations/         # dbmate SQL (-- migrate:up / migrate:down)
  tests/
agent/
  skills/             # OpenCode skills (bundled in agent image)
  app/
    mcp/              # MCP server
    toolbase/         # MCP Git/CI tools
    providers/        # GitHub Git + CI adapters
    cli/              # coreview-agent CLI
  docker/             # entrypoint, opencode config
  Dockerfile
  tests/
frontend/
  src/
    routes/           # TanStack Router file-based routes
    api/              # HTTP client + generated OpenAPI types
    hooks/            # TanStack Query hooks
    components/ui/    # shadcn components
.agents/skills/       # IDE/dev agent skills (agentskills.io)
docs/                 # Architecture diagrams
```

### Provider abstractions

Implementations live behind protocols in `backend/app/providers/`:

| Module | Purpose |
|--------|---------|
| LLM | OpenAI-compatible providers via OpenCode |
| Git | GitHub (clone, diff, webhook) |
| CI | GitHub Actions status |
| Runtime | Docker (Kubernetes planned) |

## Adding a feature

1. Add SQL migration in `backend/migrations/` (dbmate format)
2. Add repository in `backend/app/repositories/`
3. Add Pydantic schemas in `backend/app/schemas/`
4. Add route in `backend/app/api/v1/` and register in `backend/app/api/router.py`
5. Add TanStack Query hook in `frontend/src/hooks/`
6. Add page under `frontend/src/routes/`
7. Run `make openapi` to refresh TypeScript types
8. Run `make lint` and `make test-unit` (or `make test` if DB code changed)

## Code style

### Python

- Ruff: line length 88, target Python 3.11; rules `E`, `F`, `I`, `UP`
- Use `uv run` for all commands inside `backend/`
- Repositories return frozen `@dataclass` rows; services hold business logic
- Async throughout: asyncpg, httpx, FastAPI `async def` handlers

### TypeScript

- Strict TypeScript; `@/` alias maps to `src/`
- React Compiler enabled — avoid unnecessary manual `memo`/`useMemo`
- Data fetching via TanStack Query hooks, not ad-hoc `useEffect` + `fetch`
- API types from `src/api/generated/schema.ts` (generated — do not edit)
- shadcn/ui New York style (`frontend/components.json`)
- Do not hand-edit `routeTree.gen.ts` (TanStack Router plugin)

## Testing and linting

```bash
make lint          # Ruff + ESLint + typecheck
make test-unit     # pytest, integration tests skipped
make test          # unit + integration (requires Postgres)
make openapi       # export OpenAPI + regenerate TS types
```

Focused backend tests:

```bash
cd backend && uv run pytest
cd backend && uv run pytest -m integration
cd backend && uv run pytest tests/api/test_reviews.py -k webhook
```

## Common commands

| Command | Description |
|---------|-------------|
| `make dev-watch` | Docker dev with Compose Watch |
| `make dev` | Docker dev without watch |
| `make dev-down` / `make down` | Stop Docker stack |
| `make prod-up` / `make up` | Production stack (auto migrate + opencode config + agent build) |
| `make migrate` / `make migrate-down` | dbmate up / down via Compose |
| `make render-opencode-config` | Regenerate `opencode.generated.json` via Compose |
| `make build-agent` | Build agent image via Compose |

## Pull requests

CI runs on every pull request ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): lint, unit tests, integration tests (Postgres), and a Docker build smoke check. Merging to `main` triggers a publish workflow that pushes `ghcr.io/nexo-agent/nexo-coreview` and `ghcr.io/nexo-agent/nexo-coreview-agent` after CI passes. See [RELEASING.md](RELEASING.md) for the full Git flow and release process.

Before opening a PR:

1. `make lint` passes
2. `make test-unit` passes; run `make test` if you changed repositories or migrations
3. `make openapi` if API contracts changed
4. Migrations apply cleanly with `make migrate`

Commit messages: concise, imperative, explain *why*.

## Security notes

- Validate webhook payloads (GitHub HMAC) — endpoint: `POST /api/v1/webhooks/github`
- Do not commit `.env`, tokens, or webhook secrets
- Keep dynamic credentials in Postgres (Settings), not in source code
- Worker uses Docker socket for isolated git — keep runtime images minimal

## Further reading

- [RELEASING.md](RELEASING.md) — Git flow, PR process, semver releases, GHCR publish
- [AGENTS.md](AGENTS.md) — context for AI coding agents
- [`docs/architecture.svg`](docs/architecture.svg) — system architecture
- [`docs/flow.svg`](docs/flow.svg) — review flow
