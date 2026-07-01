import logging
from uuid import UUID

from celery.exceptions import MaxRetriesExceededError

from app.database import run_db, run_with_connection
from app.jobs.celery_app import celery_app
from app.repositories.reviews import ReviewRepository
from app.services.review_runner import dispatch_review_job

logger = logging.getLogger(__name__)


async def _mark_review_failed(review_id: str, error_message: str) -> None:
    await run_with_connection(
        _update_review_failed,
        UUID(review_id),
        error_message,
    )


async def _update_review_failed(conn, review_id: UUID, error_message: str) -> None:
    repo = ReviewRepository(conn)
    await repo.update_status(
        review_id,
        status="failed",
        error_message=error_message,
        set_completed=True,
    )


@celery_app.task(bind=True, max_retries=2, name="review.run")
def run_review(self, review_id: str) -> None:
    try:
        waits = run_db(dispatch_review_job(review_id))
        if not waits:
            logger.info(
                "Review %s submitted asynchronously; completion via callback",
                review_id,
            )
    except Exception as exc:
        logger.exception("Review %s failed", review_id)
        try:
            raise self.retry(exc=exc, countdown=30) from exc
        except MaxRetriesExceededError:
            message = str(exc) or "Review dispatch failed"
            run_db(_mark_review_failed(review_id, message))
            raise
