# Backend

## Responsibility

The backend is the operational core of the system.

It is responsible for:

- browser-facing REST APIs
- authentication and session management
- authorization and RBAC enforcement
- webhook ingestion from Git providers
- persistence of reviews, findings, users, teams, and settings
- agent callback processing
- serving the built frontend SPA

## Technology stack

- FastAPI for HTTP APIs
- asyncpg for PostgreSQL access
- Pydantic for request and response schemas
- Redis for sessions and Celery broker state
- Celery for background review dispatch
- Typer for CLI entrypoints

## Packaging and runtime

The production image bundles:

- Python backend code
- built frontend static assets
- `dbmate` for migrations

The API process serves the SPA from `STATIC_DIR` and exposes all API routes under `/api/v1`.

## Application structure

The backend follows a layered structure:

- `api/`: route handlers and HTTP concerns
- `services/`: business logic
- `repositories/`: SQL and persistence mapping
- `schemas/`: Pydantic contracts
- `auth/`: login, session, OIDC, SAML helpers
- `rbac/`: permission catalog, checker, effective permission computation
- `jobs/`: Celery app and task entrypoints
- `providers/`: runtime and external provider assembly

This keeps route handlers thin and pushes business behavior into services.

## Main backend flows

### Review creation flow

1. a webhook hits a provider-specific endpoint
2. the backend verifies the integration and webhook signature
3. a review row is created with `pending` status
4. a Celery task is enqueued

### Review completion flow

1. the agent sends `review.started`, `review.completed`, or `review.failed`
2. the backend validates the callback signature and payload
3. the backend updates review status and metadata
4. findings are replaced atomically for completed runs

### Settings flow

The backend stores operational settings in PostgreSQL:

- LLM providers
- repository integrations
- identity provider configuration
- RBAC permission matrix

LLM provider changes also regenerate an OpenCode configuration artifact on the API host for debugging and synchronization purposes.
The shared config builders for that artifact live in `shared/coreview_shared/agent/config.py`.

## Authentication

The backend supports three modes:

- first-run local bootstrap
- local administrator login
- SSO login through OIDC or SAML

When `auth_enabled` is false and setup is complete, the backend creates or reuses a development admin identity for local use.

## Authorization

Authorization is action-based and enforced in the backend through RBAC.

Examples:

- org-scoped settings actions
- team-scoped repository actions
- review read and rerun actions

The frontend may hide controls based on effective permissions, but the backend remains the source of truth.

## Data access conventions

Repository classes:

- use asyncpg directly
- return frozen dataclass rows
- keep SQL close to the data shape being loaded

Service classes or functions:

- orchestrate repositories
- apply business rules
- normalize output for API schemas

## API conventions

- version prefix: `/api/v1`
- pagination shape: `{ items, total }`
- permission failures: `403`
- missing resources: `404`
- ignored webhooks: `202`

## Background job boundary

The backend itself does not run reviews inline.

Instead it:

- prepares review records
- resolves runtime configuration
- delegates execution to the worker and runtime provider

This keeps webhook handling fast and avoids long-running request handlers.

## Current implementation notes

- the backend is multi-team
- organization model is effectively single-organization per deployment
- repository integrations are team-scoped
- review records are team-scoped
- built frontend assets are served from the same FastAPI app

## Important source locations

- app factory: `backend/app/main.py`
- router registration: `backend/app/api/router.py`
- lifespan and pool setup: `backend/app/lifespan.py`
- database helpers: `backend/app/database.py`
- review job dispatch: `backend/app/services/review_runner.py`
- callback handling: `backend/app/services/review_callback_handler.py`
