# Docker Compose deployment

Production-oriented Docker Compose stack for Cogito Review. All application images are pulled from [GHCR](https://ghcr.io/cogitoforge-ai) (`:latest` by default; pin a release tag or digest in `.env` for production).

For Kubernetes, see [`../k8s/README.md`](../k8s/README.md).

## Prerequisites

- Docker Engine 24+ with Compose v2
- Host access to `/var/run/docker.sock` (worker spawns one-shot review agent containers)
- Pull access to `ghcr.io/cogitoforge-ai/*` (public images; `docker login ghcr.io` if your environment requires it)

## Quick start

```bash
cd deploy/docker
cp .env.example .env
# Edit .env: secrets, COGITO_REVIEW_FRONTEND_URL, bootstrap admin email

docker compose pull
docker compose up -d
```

Open the UI at the URL configured in `COGITO_REVIEW_FRONTEND_URL` (default `http://localhost:8000` when `APP_PORT=8000`).

## Services

| Service | Image | Role |
| --- | --- | --- |
| `api` | `ghcr.io/cogitoforge-ai/cogito-review:latest` | REST API, SPA, webhooks, agent callbacks |
| `worker` | `ghcr.io/cogitoforge-ai/cogito-review:latest` | Celery consumer; spawns agent containers |
| `migrate` | `ghcr.io/cogitoforge-ai/cogito-review:latest` | One-shot `dbmate` migrations |
| `db` | `postgres:16-alpine` | PostgreSQL |
| `redis` | `redis:7-alpine` | Celery broker and sessions |

Review agents use `ghcr.io/cogitoforge-ai/cogito-review-agent:latest`, launched on demand by the worker (not a long-running Compose service).

### Startup order

1. PostgreSQL becomes healthy
2. `migrate` completes successfully
3. Redis becomes healthy
4. `api` becomes healthy
5. `worker` starts

## Monitoring profile

Optional Prometheus + Grafana stack for operational metrics. Application metrics are documented in [`../../docs/observability.md`](../../docs/observability.md).

```bash
docker compose --profile monitoring up -d
```

| Service | Port (host) | Purpose |
| --- | --- | --- |
| `prometheus` | `9091` | Scrapes API/worker `/metrics`, Postgres and Redis exporters |
| `grafana` | `3000` | Dashboards (`admin` / `GRAFANA_ADMIN_PASSWORD`) |
| `postgres-exporter` | internal | PostgreSQL metrics |
| `redis-exporter` | internal | Redis metrics |

Metrics for API and worker listen on port `9090` inside the Compose network only (`expose`, not published to the host).

## Tools profile

Roll back the latest migration (destructive):

```bash
docker compose --profile tools run --rm migrate-down
```

## Configuration

Copy [`.env.example`](.env.example) to `.env`. Required secrets use Compose interpolation errors when missing so the stack fails fast instead of starting with defaults.

Important production settings:

| Variable | Notes |
| --- | --- |
| `COGITO_REVIEW_FRONTEND_URL` | Public browser URL (OIDC/SAML redirects) |
| `COGITO_REVIEW_AUTH_ENABLED` | Defaults to `true` |
| `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY` | Encrypts stored integration secrets (32+ chars) |
| `COGITO_REVIEW_SESSION_SECRET` | Session signing key |
| `COGITO_REVIEW_AGENT_CALLBACK_SECRET` | HMAC for agent → API callbacks |
| `COGITO_REVIEW_BOOTSTRAP_ORG_ADMIN_EMAIL` | Initial org admin when DB is empty |
| `COGITO_REVIEW_IMAGE` / `COGITO_REVIEW_AGENT_IMAGE` | Pin semver tags instead of `:latest` |

## Security notes

- The worker mounts the Docker socket to run review agents. Treat this host as privileged.
- Do not expose `/metrics` (port `9090`) through a public reverse proxy.
- Restrict Postgres/Redis to the internal `cogito-review` network (default in this compose file).
- Set strong, unique values for all secrets in `.env`. Do not commit `.env`.

## Resource sizing

Default limits target a small production instance (similar to the reference Kubernetes manifests). Adjust `WORKER_CONCURRENCY`, `COGITO_REVIEW_AGENT_*`, and Postgres/Redis resources for your workload.

## Related documentation

- [`../../docs/deployment.md`](../../docs/deployment.md) — deployment topology
- [`../../docs/observability.md`](../../docs/observability.md) — metric catalog and scrape targets
