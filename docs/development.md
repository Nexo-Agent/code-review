# Development

## Monorepo layout

The repository is organized as a small workspace monorepo.

- `shared/`: cross-cutting Python package used by backend and agent
- `backend/`: API, worker entrypoints, services, migrations, tests
- `agent/`: isolated review runner and MCP server
- `frontend/`: React SPA
- `docs/`: project documentation

## Core development workflow

### Recommended local setup

The recommended workflow is Docker-based development with hot reload:

```bash
cp .env.example .env
make dev
```

This starts:

- backend API with reload
- frontend with Vite HMR
- worker
- PostgreSQL
- Redis

### Host-side tooling

For linting, tests, and code generation, the repository expects:

- `uv`
- Node.js 22+
- Docker Compose

## Build and run commands

Common commands:

- `make dev`
- `make prod`
- `make prod-down`
- `make migrate`
- `make migrate-down`
- `make build-agent`
- `make openapi`
- `make lint`
- `make test-unit`
- `make test`

## Package management

### Python

Python dependencies are managed with `uv`.

- root workspace file: `pyproject.toml`
- lock file: `uv.lock`
- Python packages: `shared`, `backend`, `agent`

### Frontend

Frontend dependencies are managed separately in `frontend/`.

Current lockfile in repo:

- `frontend/yarn.lock`

## API contract generation

Frontend API types are generated from the backend OpenAPI schema.

Flow:

1. export backend OpenAPI to `openapi.json`
2. generate `frontend/src/api/generated/schema.ts`

Command:

```bash
make openapi
```

## Testing

Current test layout:

- `shared/tests/`
- `backend/tests/`
- `agent/tests/`

Commands:

- `make test-unit` for unit-focused coverage
- `make test` for unit plus integration test suites

Representative coverage areas in the current repository:

- Git provider behavior
- callback HMAC verification
- worktree management
- webhook handling
- review retry behavior
- identity provider configuration
- RBAC enforcement

## Linting and static checks

Commands:

- `make lint`

This runs:

- Ruff for Python packages
- ESLint for the frontend
- TypeScript type checking

## Frontend development conventions

- file-based routing with TanStack Router
- data fetching through TanStack Query hooks
- generated API types instead of handwritten response shapes
- reusable UI primitives in `components/ui`

## Backend development conventions

- keep route handlers small
- put business logic in services
- keep SQL in repositories
- use Pydantic schemas for API boundaries
- prefer provider abstractions for Git, CI, and runtime integrations

## Agent development conventions

- the agent must remain database-independent
- report state through callbacks only
- keep review execution one-shot and isolated
- place OpenCode behavior in the bundled skill and config layers rather than hard-coding review logic into the backend

## Authentication-aware development

The codebase supports two common development modes:

- `auth_enabled=false`: local dev bypass with a generated admin identity after setup completes
- `auth_enabled=true`: real login through local admin or configured SSO

This is useful when working on UI flows, permissions, and settings screens.

## Database evolution

Schema changes should be made through forward migrations in `backend/migrations/`.

Typical workflow for data model changes:

1. add migration
2. update repositories
3. update services and schemas
4. update API and frontend types if needed
5. run tests

## Review feature development

When changing review execution, the main boundary to keep in mind is:

- backend prepares and records review jobs
- worker launches execution
- agent performs the review
- backend persists callback results

Changes that cross this boundary usually affect more than one package.

## Current maturity notes

Implemented and used actively:

- Docker-first local development
- hot reload for frontend and backend
- OpenAPI type generation
- automated lint and test targets

Not yet generalized:

- Kubernetes-first development flow
- provider-specific local fixtures for every external system
