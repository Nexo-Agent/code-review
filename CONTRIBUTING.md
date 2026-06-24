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

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (native dev)
- Node.js 22+ and Yarn (native dev)
- Docker Compose v2.22+ (recommended; `watch` support for file sync)

## Getting started

### Docker dev (recommended)

Full stack with Vite HMR, Uvicorn `--reload`, and Docker Compose Watch:

```bash
cp .env.example .env
make dev-migrate    # first time only
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

`make dev-watch` merges [`docker-compose.yaml`](docker-compose.yaml) with [`docker-compose.override.yaml`](docker-compose.override.yaml). Bind mounts enable instant reload; `develop.watch` rebuilds images when `uv.lock` or `yarn.lock` change.

On Docker Desktop (macOS/Windows), set `CHOKIDAR_USEPOLLING=true` in `.env` if HMR misses file changes.

### Native local development

```bash
cp .env.example .env
make dev-db         # Postgres + Redis
make migrate
make dev-api        # terminal 1
make dev-web        # terminal 2
```

Install dependencies directly:

```bash
cd backend && uv sync
cd frontend && yarn install
```

### Production

```bash
make prod-up   # docker compose -f docker-compose.yaml --profile prod up -d
```

Production uses only the base compose file; `docker-compose.override.yaml` is not merged.

## Compose layout

| File | Purpose |
|------|---------|
| [`docker-compose.yaml`](docker-compose.yaml) | Base: `db`, `app` (profile `prod`), `migrate` (profile `tools`) |
| [`docker-compose.override.yaml`](docker-compose.override.yaml) | Dev: `api`, `web`, worker, MCP, OpenCode, Compose Watch |
| [`dev.Dockerfile`](dev.Dockerfile) | Multi-stage dev images (`target: api` / `target: web`) |
| [`Dockerfile`](Dockerfile) | Production bundle (API + static SPA) |

Docker dev stack services: `api`, `worker`, `mcp-serve`, `opencode-serve`, `redis`, `db`. The worker mounts `/var/run/docker.sock` for isolated git workspaces. OpenCode connects to `mcp-serve` for MCP tools (`coreview-git_*`, `coreview-ci_*`).

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
| `NEXO_COREVIEW_OPENCODE_SERVER_URL` | OpenCode `serve` base URL |
| `NEXO_COREVIEW_OPENCODE_CONFIG_PATH` | Path to generated OpenCode config |
| `NEXO_COREVIEW_DOCKER_HOST` | Docker Engine URL; empty = auto-detect per platform |
| `NEXO_COREVIEW_GIT_IMAGE` | Minimal git image (default `alpine/git:latest`) |
| `NEXO_COREVIEW_MCP_SERVER_URL` | MCP SSE URL (default `http://mcp-serve:8001/sse`) |
| `MCP_PORT` | Host port for MCP server (default `8001`) |

Optional one-time bootstrap vars (`NEXO_COREVIEW_GITHUB_*`, `NEXO_COREVIEW_LLM_*`) seed the database on first load if settings are empty.

### Dynamic settings (database)

Configured via **Settings** (`/settings`) or the API:

- **LLM providers** — `GET/POST /api/v1/settings/llm-providers`, `PUT/DELETE .../{id}`
- **Repositories** — `GET/POST /api/v1/settings/repos`, `PUT/DELETE .../{id}`

Saving LLM providers regenerates `opencode.generated.json`; restart `opencode-serve` to apply.

## CLI modes

```bash
cd backend && uv run code-review backend run
cd backend && uv run code-review job worker
cd backend && uv run code-review agent run --review-id <uuid>
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
    toolbase/         # MCP Git/CI tools
    mcp/              # MCP server
    cli/              # Typer commands
  migrations/         # dbmate SQL (-- migrate:up / migrate:down)
  tests/
frontend/
  src/
    routes/           # TanStack Router file-based routes
    api/              # HTTP client + generated OpenAPI types
    hooks/            # TanStack Query hooks
    components/ui/    # shadcn components
.agents/skills/       # Agent skills (agentskills.io)
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
| `make dev-down` | Stop Docker dev stack |
| `make dev-migrate` | Run migrations in compose network |
| `make dev-db` | Start Postgres + Redis only |
| `make dev-api` | Uvicorn with reload (native) |
| `make dev-web` | Vite dev server (native) |
| `make dev-worker` | Celery worker (native) |
| `make dev-mcp-serve` | Nexo Co-Review MCP server (`nexo-coreview`) |
| `make render-opencode-config` | Generate `opencode.generated.json` |
| `make migrate` / `make migrate-down` | dbmate up / down |
| `make prod-up` | Production compose |

## Pull requests

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

- [AGENTS.md](AGENTS.md) — context for AI coding agents
- [`docs/architecture.svg`](docs/architecture.svg) — system architecture
- [`docs/flow.svg`](docs/flow.svg) — review flow
