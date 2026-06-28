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

    request = event.request

    if event.event == "review.started":
        await repo.update_request_metadata(
            review_id,
            pr_title=request.pr_title,
            pr_url=request.pr_url,
            pr_author=request.pr_author,
            head_sha=request.head_sha,
            base_sha=request.base_sha,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
        )
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
        await repo.update_request_metadata(
            review_id,
            pr_title=request.pr_title,
            pr_url=request.pr_url,
            pr_author=request.pr_author,
            head_sha=request.head_sha,
            base_sha=request.base_sha,
            base_ref=request.base_ref,
            head_ref=request.head_ref,
        )
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
            github = event.result.github
            await repo.update_delivery_stats(
                review_id,
                summary_comment_posted=github.summary_comment_posted,
                inline_comments_posted=github.inline_comments_posted,
                inline_comments_skipped=github.inline_comments_skipped,
            )
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
