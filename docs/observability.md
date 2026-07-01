# Observability

## Purpose

This document describes **operational** Prometheus metrics exposed by Cogito Review for self-hosted deployments.

It is separate from [`metrics.md`](metrics.md), which defines **product effectiveness** analytics (PR time to merge, helpful rate, and similar workflow outcomes stored in PostgreSQL and shown in the web UI).

Cogito Review exposes pull-scrape `/metrics` endpoints only. You deploy and configure Prometheus (or any compatible scraper) yourself. This repository does not ship Prometheus, Grafana, Pushgateway, `ServiceMonitor`, or alerting rules.

## Exposed endpoints

| Component | Port | Path | Notes |
| --- | --- | --- | --- |
| API | `9090` | `/metrics` | Same container image as the worker; HTTP app remains on `8000` |
| Worker | `9090` | `/metrics` | Celery process; no public HTTP API |
| Operator | `8080` | `/metrics` | HTTP (not TLS) by default; health probes on `8081` |

Agent review containers do **not** expose metrics in the current release. Agent observability may be added in a later phase.

### Security

- Bind metrics on an internal port. Do not route `/metrics` through the application ingress.
- In Docker Compose, port `9090` is exposed on the internal network only (`expose`, not `ports` on the host).
- In Kubernetes, scrape via ClusterIP Service or pod discovery inside the cluster. Restrict access with network policies if needed.
- Metrics endpoints are unauthenticated. Treat them like any other internal ops surface.

## Configuration

Environment variables (prefix `COGITO_REVIEW_`):

| Variable | Default | Description |
| --- | --- | --- |
| `METRICS_ENABLED` | `true` | When `false`, the API does not start the metrics server or HTTP middleware; the worker skips its metrics server and Celery hooks have no effect on export |
| `METRICS_BIND_HOST` | `0.0.0.0` | Listen address for API/worker metrics |
| `METRICS_BIND_PORT` | `9090` | Listen port for API/worker metrics |

Operator flags (override via Deployment args):

- `--metrics-bind-address=:8080`
- `--metrics-secure=false`

## Metric catalog (P0)

All custom metrics use the `cogito_` prefix.

### API — HTTP

| Metric | Labels | Description |
| --- | --- | --- |
| `cogito_http_requests_total` | `method`, `handler`, `status` | Request count (`handler` is the matched route template, or `unmatched`) |
| `cogito_http_request_duration_seconds` | `method`, `handler` | Request latency histogram |

### API — Webhooks

| Metric | Labels | Description |
| --- | --- | --- |
| `cogito_webhook_events_total` | `provider`, `outcome` | Webhook handling outcomes |

`outcome` values:

- `enqueued` — new review created and Celery job queued
- `deduped` — duplicate delivery or same repo/PR/SHA
- `ignored` — disabled repo, wrong provider, or non-actionable event
- `no_llm` — valid event but no LLM provider configured
- `auth_failed` — signature verification failed
- `analytics_only` — analytics event stored without review enqueue

`provider` matches the Git integration id (`github`, `gitlab`, `azure-devops`, `bitbucket`, `bitbucket-dc`).

### Worker — Celery and dispatch

| Metric | Labels | Description |
| --- | --- | --- |
| `cogito_celery_tasks_total` | `task`, `status` | Terminal task outcomes (`succeeded`, `failed`, `retried`) |
| `cogito_celery_task_duration_seconds` | `task` | Task runtime histogram |
| `cogito_review_dispatch_total` | `backend` | Accepted review submissions (`docker`, `kubernetes`) |
| `cogito_review_dispatch_errors_total` | — | Failed review dispatch attempts |

### Operator

Controller-runtime exposes standard metrics, including:

- `controller_runtime_reconcile_total`
- `workqueue_depth`
- `workqueue_adds_total`

No custom Cogito Review reconcile metrics are defined in P0.

## Example scrape configuration

### Docker Compose

Prometheus must reach the Compose network (attach the same network or run Prometheus inside it):

```yaml
scrape_configs:
  - job_name: cogito-review
    static_configs:
      - targets:
          - api:9090
          - worker:9090
```

### Kubernetes

API (Service exposes port `metrics`):

```yaml
scrape_configs:
  - job_name: cogito-review-api
    static_configs:
      - targets:
          - cogito-review-api.cogito-review.svc:9090
  - job_name: cogito-review-operator
    static_configs:
      - targets:
          - cogito-review-operator-metrics.cogito-review-system.svc:8080
```

Worker pods have no dedicated Service in the reference manifests. Use pod discovery or add a Service if you need a stable scrape target.

## Out of scope (P0)

- Agent container metrics (Pushgateway or otherwise)
- Product analytics export to Prometheus (see [`metrics.md`](metrics.md))
- Bundled Prometheus, Grafana, or Pushgateway
- `ServiceMonitor`, `PrometheusRule`, or sample dashboards
- Postgres/Redis exporters (deploy separately if needed)

## Related documentation

- [`deployment.md`](deployment.md) — deployment topology
- [`metrics.md`](metrics.md) — product effectiveness metrics
- [`kubernetes.md`](kubernetes.md) — Kubernetes integration
