import logging

from celery import Celery

from app.config import get_code_review_settings

logger = logging.getLogger(__name__)

settings = get_code_review_settings()

celery_app = Celery(
    "code_review",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=["app.jobs.review", "app.jobs.review_analytics", "app.jobs.usage_metrics"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=settings.review_timeout_seconds,
    task_time_limit=settings.review_timeout_seconds + 60,
    beat_schedule={
        "review-analytics-recompute": {
            "task": "review.analytics.recompute",
            "schedule": settings.analytics_rollup_interval_seconds,
            "args": (settings.analytics_rollup_window_days, None),
        },
        "usage-metrics-recompute": {
            "task": "usage.metrics.recompute",
            "schedule": settings.usage_rollup_interval_seconds,
            "args": (settings.usage_rollup_window_days, None),
        },
    },
)
