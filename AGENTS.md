# AGENTS.md

Instructions for AI coding agents working on this repository.

## Project overview

Monorepo for an LLM-powered code review pilot (**Cogito Review**, codename `cogito-review`):

- **Agent** — Python 3.11+, MCP server (`cogito-review-agent`), OpenCode runtime image
- **Backend** — Python 3.11+, FastAPI, asyncpg, Celery, Typer CLI (`cogito-review`)
- **Frontend** — React 19, Vite, TanStack Router/Query/Table, shadcn/ui (New York)
- **Database** — PostgreSQL (dbmate migrations)
- **Agent runtime** — [OpenCode](https://opencode.ai/) + MCP toolbase (Git/CI tools)

Production ships as a single Docker image (API + bundled SPA). Architecture diagrams: `docs/architecture.svg`, `docs/flow.svg`.

### Runtime architecture

Three layers with clear boundaries:

1. **Backend (API)** — Configuration management, webhooks, frontend API. Stores organizations, teams, projects, repo integrations, and LLM providers in Postgres.
2. **Job (Celery worker)** — Reads review + integration config from DB, builds a full `COGITO_REVIEW_*` env dict, spawns a one-shot agent container via the Docker runtime provider.
3. **Agent (stateless container)** — Receives all execution config via env (materializes ephemeral `opencode.json` locally). Uses a persistent repo mirror + per-PR git worktree under `/workspaces`, runs LLM review, posts to GitHub. Reports progress and findings via **HTTP callback** (schema v1, HMAC-signed); it does **not** connect to Postgres.

The agent does **not** read `repo_integrations` or `llm_providers` from the database.

### Review callback (schema v1)

Agent posts `review.started`, `review.completed`, and `review.failed` events to `COGITO_REVIEW_CALLBACK_URL` with `X-Review-Signature-256` HMAC auth. Spec: [`shared/coreview_shared/schemas/review-callback-v1.schema.json`](shared/coreview_shared/schemas/review-callback-v1.schema.json) (Pydantic models in `review_callback.py`). The Cogito Review backend receives them at `POST /api/v1/agent/review-events` and persists to Postgres. Third-party orchestrators can implement the same callback contract without the Cogito Review database schema.

### CLI modes

```bash
cd backend && uv run cogito-review backend run   # FastAPI server
cd backend && uv run cogito-review job worker    # Celery worker (prepare env + spawn agent)
cd agent && uv run cogito-review-agent review run --review-id <uuid>  # one-shot review (env injected by job)
```

### Provider abstractions

Protocols, GitHub Git/CI implementations, runtime specs (Docker/K8s), OpenCode LLM provider, and callback schemas live in **`shared/`** (`coreview-shared` package). Backend and agent wire them via local `factory.py` and app-specific config.

| Module (in `coreview_shared`) | Purpose |
|--------|---------|
| `llm/opencode` | OpenCode CLI review runner |
| `providers/git`, `providers/ci` | GitHub worktree checkout, diff, webhook, CI summary |
| `runtime/docker`, `runtime/k8s` | Job execution and persistent workspace volume |
| `schemas/review_callback` | Agent callback contract (v1) |

Backend-specific: `backend/app/providers/factory.py`, `opencode_config.py` (multi-provider DB merge). Agent-specific: `agent/app/providers/factory.py`, MCP toolbase in `agent/app/toolbase/`.

**Agent env validation (`agent/app/services/review_env.py`):** `require_review_env()` checks provider-specific Git credentials before the agent container runs. When adding a Git provider, update **both** `backend/app/services/review_job_prepare.py` (`build_agent_environment`) and `require_review_env()` — otherwise the worker enqueues the job but the agent exits immediately (review stuck in `pending` because no callback is sent). Required vars per provider:

| `COGITO_REVIEW_GIT_PROVIDER` | Git credential env var(s) |
|------------------------------|---------------------------|
| `github` (default) | `COGITO_REVIEW_GITHUB_TOKEN` |
| `gitlab` | `COGITO_REVIEW_GITLAB_TOKEN` (optional `COGITO_REVIEW_GITLAB_BASE_URL` for self-hosted) |
| `azure-devops` | `COGITO_REVIEW_ADO_ORGANIZATION`, `COGITO_REVIEW_ADO_PROJECT`, `COGITO_REVIEW_ADO_PAT` |

Agent skills bundled into the Docker image live in `agent/skills/code-reviewer/` (OpenCode). IDE/dev skills remain in `.agents/skills/`. MCP tools are in `agent/app/toolbase/`.

### Organization / Team / Project hierarchy

Self-hosted deployments use a single **organization** (singleton per install):

| Entity | Purpose |
|--------|---------|
| **Organization** | Owns the LLM provider pool (`llm_providers.organization_id`) |
| **Team** | Isolation boundary — users only see reviews for teams they belong to |
| **Project** | Business grouping of repos; selects one LLM from the org pool (`projects.llm_provider_id`) |
| **Repository** (`repo_integrations`) | Git credentials, system prompt, webhook secret; scoped to a project |

Migration `008_teams_projects_auth.sql` backfills a default org/team/project for existing installs. Reviews store denormalized `team_id` and `project_id`.

**LLM resolution at review time:** `project.llm_provider_id` → org default (`is_default=true`) via `resolve_llm_provider_for_project()`. Repos do **not** store LLM config.

**Webhooks (per integration):**

```
POST /api/v1/webhooks/github/{integration_id}
POST /api/v1/webhooks/azure-devops/{integration_id}
POST /api/v1/webhooks/gitlab/{integration_id}
```

Global `/webhooks/github` and `/webhooks/azure-devops` are deprecated (410). Configure the per-repo URL in the repo detail UI.

### First-boot install (`/install`)

Fresh installs with no users require a one-time setup wizard at **`/install`**. The super administrator account uses local username/password (`auth_source=local`, `is_superuser=true`). After `system_install.completed_at` is set:

- `POST /api/v1/install/bootstrap` returns **403**
- The SPA redirects `/install` → `/login`
- Local break-glass sign-in remains at `POST /api/v1/auth/local/login`

Existing databases are backfilled as already completed (migration `011_local_superuser.sql`).

### Authentication (OIDC / SAML BFF)

When `COGITO_REVIEW_AUTH_ENABLED=true`, the backend runs OIDC authorization code or SAML 2.0 SP flows and stores sessions in Redis (cookie `cogito_session`). IdP settings are stored in Postgres (`organization_identity_providers`) and configured in the UI at **Settings → SSO** (org admin). One IdP per install (OIDC presets: Google, Entra, Okta, Keycloak, Auth0, custom; or SAML 2.0). The SPA uses `credentials: "include"` and never holds access tokens.

| Route | Auth |
|-------|------|
| `/api/v1/install/status`, `/install/bootstrap` | Public (bootstrap blocked after setup) |
| `/api/v1/auth/login`, `/callback`, `/auth/idp`, `/auth/local/login`, `/logout`, `/me` | Public (except `/me` needs session) |
| `/api/v1/settings/identity-provider` | Org admin |
| `/api/v1/teams`, `/projects`, `/reviews`, `/settings/llm-providers` | Session cookie |
| `/api/v1/webhooks/*`, `/api/v1/agent/*`, `/api/v1/health` | Exempt (HMAC / machine) |

Dev default: `COGITO_REVIEW_AUTH_ENABLED=false` uses a bypass org-admin user **after setup is complete**. Before setup, API routes return 401 until bootstrap. Users are JIT-created on first SSO login; org admins assign team membership via `POST/DELETE /api/v1/teams/{team_id}/members`.

See `.env.example` for `COGITO_REVIEW_AUTH_ENABLED`, `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY`, `COGITO_REVIEW_SESSION_*`, and `COGITO_REVIEW_BOOTSTRAP_ORG_ADMIN_EMAIL`.

## Prerequisites

- Docker Compose v2.22+ (`watch` support for file sync)
- [uv](https://docs.astral.sh/uv/) and Node.js 22+ only for host-side lint/test/openapi tasks
- Python deps are managed as a **uv workspace** (`pyproject.toml` + `uv.lock` at repo root). Run `uv lock` from the repo root after changing dependencies in `shared/`, `backend/`, or `agent/`.

## Setup commands

```bash
cp .env.example .env

# Docker dev: HMR + Uvicorn reload + Compose Watch
make dev
make pre-commit-install   # optional: lint/format on git commit

# Production (base compose only):
make prod
```

| URL | Service |
|-----|---------|
| http://localhost:5173 | Frontend (Vite HMR, dev only) |
| http://localhost:8000/docs | OpenAPI / Swagger |
| http://localhost:8000/api/v1/health | Health check |

On `make prod`, Compose pulls GHCR images and runs **dbmate migrate** before `app` and `worker` start. OpenCode config is synced on API startup from Postgres.

On Docker Desktop (macOS/Windows), set `CHOKIDAR_USEPOLLING=true` in `.env` if HMR misses file changes.

## Dev environment tips

- Root `.env` is loaded by Makefile, backend (`pydantic-settings`), and Compose.
- **Infrastructure env vars** use prefix `COGITO_REVIEW_*` (Redis, Docker, OpenCode, MCP). See `.env.example`.
- **Dynamic settings** (repos, webhook secrets, GitHub tokens, LLM providers, teams, projects) are stored in Postgres and edited in the UI — do not hardcode secrets.
- **Frontend routes:** `/teams`, `/teams/$teamId/projects/$projectId/repos/$repoId`, `/reviews`, `/llm-providers` (org admin only). Legacy `/repositories/*` redirects to `/teams`.
- After changing API routes or Pydantic schemas, run `make openapi` to refresh `openapi.json` and `frontend/src/api/generated/schema.ts`.
- After adding LLM providers via Settings, each new review spawns a fresh agent container with the latest config injected via env.
- Compose layout: `docker-compose.yaml` (base) + `docker-compose.override.yaml` (dev, auto-merged). Production uses only the base file: `make prod`.
- `routeTree.gen.ts` is generated by TanStack Router — do not hand-edit.

## Project structure

```
shared/                 # coreview-shared — protocols, providers, callback schemas (not a runtime service)
  coreview_shared/
backend/
  app/
    auth/             # OIDC client, Redis session, FastAPI dependencies
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
  skills/code-reviewer/  # OpenCode review skill (bundled in agent image)
  app/
    mcp/              # MCP server (FastMCP)
    toolbase/         # Git/CI MCP tool handlers
    providers/        # factory wiring from env
    repositories/     # repo_integrations (per-repo credentials)
    cli/              # cogito-review-agent Typer CLI
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
- Config via `app.config.Settings` and `CodeReviewSettings` (`COGITO_REVIEW_` prefix)
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
- Webhook endpoints: `POST /api/v1/webhooks/github/{integration_id}` (and ADO variant)
- Enable OIDC/SAML in production: `COGITO_REVIEW_AUTH_ENABLED=true`; configure IdP in Settings → SSO; set strong `COGITO_REVIEW_SESSION_SECRET` and `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY`
- Never log or commit `COGITO_REVIEW_*` tokens, webhook secrets, or GitHub PATs
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
| `make dev` | Docker dev with Compose Watch |
| `make prod` | Production stack (base compose only) |
| `make prod-down` | Stop the production-like stack |
| `make migrate` / `make migrate-down` | dbmate up / down via Compose |
| `make render-opencode-config` | Regenerate `opencode.generated.json` on host (optional debug) |
| `make build-agent` | Build agent image locally (`docker build`) |
| `make openapi` | Export OpenAPI + regenerate TS types (host) |
| `make pre-commit-install` | Install git pre-commit hooks (host) |
| `make pre-commit` | Run pre-commit on all files (host) |
