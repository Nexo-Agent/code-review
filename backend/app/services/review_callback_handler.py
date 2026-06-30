import logging
from uuid import UUID

from coreview_shared.schemas.review_callback import ReviewCallbackEvent

from app.repositories.repo_integrations import RepoIntegrationRepository
from app.repositories.reviews import ReviewRepository
from app.services.review_analytics_events import persist_comment_artifacts_and_events

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
        finding_rows = []
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
        finding_rows = await repo.replace_findings(review_id, findings)
        repo_integration = None
        if row.repo_integration_id is not None:
            repo_integration = await RepoIntegrationRepository(conn).get(
                row.repo_integration_id
            )
        finding_ids_by_index = {
            index: finding_row.id for index, finding_row in enumerate(finding_rows)
        }
        if event.result is not None and event.result.github.comment_artifacts:
            await persist_comment_artifacts_and_events(
                conn,
                review=row,
                repo_integration=repo_integration,
                artifacts=[
                    artifact.model_dump(mode="python")
                    for artifact in event.result.github.comment_artifacts
                ],
                finding_ids_by_index=finding_ids_by_index,
            )
        await repo.update_status(review_id, status="completed", set_completed=True)
        logger.info(
            "Review %s completed via callback with %d finding(s)",
            event.review_id,
            len(findings),
        )
        return

    msg = f"Unsupported callback event: {event.event}"
    raise ValueError(msg)
