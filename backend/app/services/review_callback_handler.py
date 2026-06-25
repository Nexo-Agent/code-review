import logging
from uuid import UUID

from coreview_shared.schemas.review_callback import ReviewCallbackEvent

from app.repositories.reviews import ReviewRepository

logger = logging.getLogger(__name__)


async def handle_review_callback(conn, event: ReviewCallbackEvent) -> None:
    repo = ReviewRepository(conn)
    review_id = UUID(event.review_id)
    row = await repo.get(review_id)
    if row is None:
        msg = f"Review not found: {event.review_id}"
        raise LookupError(msg)

    if event.event == "review.started":
        await repo.update_status(review_id, status="running", set_started=True)
        logger.info("Review %s marked running via callback", event.review_id)
        return

    if event.event == "review.failed":
        message = event.error.message if event.error else "Review failed"
        await repo.update_status(
            review_id,
            status="failed",
            error_message=message,
            set_completed=True,
        )
        logger.info("Review %s marked failed via callback", event.review_id)
        return

    if event.event == "review.completed":
        findings = []
        if event.result is not None:
            findings = [
                {
                    "severity": f.severity,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "title": f.title,
                    "body": f.body,
                }
                for f in event.result.findings
            ]
        await repo.replace_findings(review_id, findings)
        await repo.update_status(review_id, status="completed", set_completed=True)
        logger.info(
            "Review %s completed via callback with %d finding(s)",
            event.review_id,
            len(findings),
        )
        return

    msg = f"Unsupported callback event: {event.event}"
    raise ValueError(msg)
