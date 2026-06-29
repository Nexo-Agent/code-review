import logging

from app.database import run_db
from app.jobs.celery_app import celery_app
from app.services.review_runner import dispatch_review_job

logger = logging.getLogger(__name__)


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
        raise self.retry(exc=exc, countdown=30) from exc
