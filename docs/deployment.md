# Deployment

## Current supported deployment path

The production-ready path in this repository is container-based deployment with Docker Compose.

Main services:

- `api`
- `worker`
- `db`
- `redis`
- `migrate` as a one-shot init job

The backend and worker use the same main application image. The review agent uses a separate image that the worker launches on demand.

## Images

Current images:

- main app image: `ghcr.io/cogitoforge-ai/cogito-review`
- agent image: `ghcr.io/cogitoforge-ai/cogito-review-agent`

The main image bundles:

- backend API
- built frontend SPA
- runtime dependencies for auth and migrations

## Compose topology

The reference deployment topology is defined in `docker-compose.yaml`.

### API service

Responsibilities:

- serve REST API
- serve frontend static assets
- receive webhooks
- receive agent callbacks

### Worker service

Responsibilities:

- consume Celery review jobs
- mount the shared workspace volume
- access the Docker socket
- spawn one-shot agent containers

### Database and Redis

- PostgreSQL stores relational state
- Redis stores session and Celery runtime state

### Migration service

`migrate` runs `dbmate` before the long-running services start.

## Workspace and socket requirements

The current Docker runtime design requires the worker to have:

- a writable workspace volume mounted at `/workspaces`
- access to `/var/run/docker.sock`

This is necessary because the worker launches one agent container per review.

## Environment configuration

Important runtime environment groups:

### Application and database

- `DATABASE_URL`
- `APP_PORT`
- pool sizing settings

### Worker and runtime

- `COGITO_REVIEW_CELERY_BROKER_URL`
- `COGITO_REVIEW_WORKSPACE_ROOT`
- `COGITO_REVIEW_DOCKER_HOST`
- `COGITO_REVIEW_AGENT_IMAGE`
- `COGITO_REVIEW_AGENT_NETWORK`
- `COGITO_REVIEW_AGENT_MEM_LIMIT`
- `COGITO_REVIEW_AGENT_CPUS`

### Agent callback security

- `COGITO_REVIEW_AGENT_CALLBACK_URL`
- `COGITO_REVIEW_AGENT_CALLBACK_SECRET`

### Auth and secrets

- `COGITO_REVIEW_AUTH_ENABLED`
- `COGITO_REVIEW_SESSION_SECRET`
- `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY`
- `COGITO_REVIEW_FRONTEND_URL`

## Build strategy

### Main application image

The root `Dockerfile` is multi-stage:

1. build frontend with Vite
2. install Python workspace dependencies with `uv`
3. assemble runtime image with backend code and built SPA

### Agent image

`agent/Dockerfile` builds a separate runtime containing:

- OpenCode binary
- Python review runner
- git and SSH tools
- bundled review skill

## Runtime support matrix

### Implemented

- Docker runtime provider
- Docker Compose deployment topology

### Defined but not fully implemented

- Kubernetes runtime provider abstraction

The codebase includes a `K8sRuntimeProvider`, but review job execution is currently `NotImplemented`.

## Podman and Kubernetes status

The repository documentation may describe broader container-runtime goals, but the current source code only provides a working execution path for Docker.

Current status:

- Docker Compose: implemented
- Podman Compose: not explicitly implemented in repository tooling
- Kubernetes: abstraction exists, execution path not implemented

## Security-sensitive deployment notes

- treat the Docker socket on the worker as privileged access
- use a strong callback secret for agent-to-backend communication
- use a dedicated encryption key for stored secrets in production
- prefer pinned image tags or digests instead of `latest`
- protect PostgreSQL and Redis with network isolation and credentials
- ensure the public `frontend_url` is set correctly for OIDC and SAML redirect generation

## Operational startup sequence

Typical startup order:

1. PostgreSQL becomes healthy
2. migrations run
3. Redis becomes healthy
4. API starts
5. worker starts
6. review agent containers are spawned only when reviews are queued

## Development deployment

Local development uses `docker-compose.override.yaml` in addition to the base compose file to enable:

- frontend HMR
- backend reload
- compose watch behavior
- local agent image builds

This is a developer workflow, not the production topology.
