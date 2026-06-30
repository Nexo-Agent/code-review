from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.database import run_db_fn
from app.jobs.celery_app import celery_app
from app.services.review_analytics_metrics import compute_review_analytics

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, name="review.analytics.recompute")
def recompute_review_analytics(
    self,
    window_days: int | None = None,
    window_end_iso: str | None = None,
) -> dict[str, object]:
    try:
        result = run_db_fn(
            compute_review_analytics,
            window_days=window_days or 30,
            window_end=(
                datetime.fromisoformat(window_end_iso).astimezone(UTC)
                if window_end_iso
                else None
            ),
        )
        return {
            "job_run_id": str(result.job_run_id),
            "window_start": result.window_start.isoformat(),
            "window_end": result.window_end.isoformat(),
            "rows_upserted": result.rows_upserted,
        }
    except Exception as exc:
        logger.exception("Review analytics recompute failed")
        raise self.retry(exc=exc, countdown=60) from exc
