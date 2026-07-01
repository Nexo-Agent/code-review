from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "cogito_http_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "handler", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "cogito_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "handler"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

WEBHOOK_EVENTS = Counter(
    "cogito_webhook_events_total",
    "Git provider webhook handling outcomes.",
    ["provider", "outcome"],
)

CELERY_TASKS = Counter(
    "cogito_celery_tasks_total",
    "Celery task terminal outcomes.",
    ["task", "status"],
)
CELERY_TASK_DURATION = Histogram(
    "cogito_celery_task_duration_seconds",
    "Celery task runtime in seconds.",
    ["task"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0),
)

REVIEW_DISPATCH = Counter(
    "cogito_review_dispatch_total",
    "Review execution submissions accepted by the runtime backend.",
    ["backend"],
)
REVIEW_DISPATCH_ERRORS = Counter(
    "cogito_review_dispatch_errors_total",
    "Review execution submission failures in the worker.",
)


def record_webhook_event(provider: str, outcome: str) -> None:
    WEBHOOK_EVENTS.labels(provider=provider, outcome=outcome).inc()


def increment_review_dispatch(backend: str) -> None:
    REVIEW_DISPATCH.labels(backend=backend).inc()


def increment_review_dispatch_error() -> None:
    REVIEW_DISPATCH_ERRORS.inc()
