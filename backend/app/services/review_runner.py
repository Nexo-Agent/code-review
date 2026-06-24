import logging
from uuid import UUID

import asyncpg

from app.config import get_settings
from app.providers.factory import build_providers
from app.providers.protocols import ProviderBundle, Workspace, WorkspaceSpec
from app.repositories.reviews import ReviewRepository
from app.services.integration_settings import (
    build_providers_config,
    get_integration_settings,
)
from app.services.review_format import format_comment

logger = logging.getLogger(__name__)


async def execute_review_logic(review_id: str) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    providers: ProviderBundle | None = None
    workspace: Workspace | None = None
    try:
        integration = await get_integration_settings(conn)
        providers = build_providers(build_providers_config(integration))

        repo = ReviewRepository(conn)
        review = await repo.get(UUID(review_id))
        if review is None:
            msg = f"Review not found: {review_id}"
            raise ValueError(msg)

        await repo.update_status(
            review.id, status="running", set_started=True
        )

        pr_context = await providers.git.fetch_pr_context(
            review.repo_full_name,
            review.pr_number,
            review.head_sha,
        )
        ci_summary = await providers.ci.get_ci_summary(
            review.repo_full_name,
            review.head_sha,
        )
        pr_context = type(pr_context)(
            metadata=pr_context.metadata,
            diff=pr_context.diff,
            ci_summary=ci_summary,
        )

        spec = WorkspaceSpec(
            review_id=str(review.id),
            repo_full_name=review.repo_full_name,
            pr_number=review.pr_number,
            head_sha=review.head_sha,
        )
        workspace = await providers.runtime.prepare_workspace(spec)
        findings = await providers.llm.run_review(workspace, pr_context)

        await repo.replace_findings(
            review.id,
            [
                {
                    "severity": f.severity,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "title": f.title,
                    "body": f.body,
                }
                for f in findings
            ],
        )
        await repo.update_status(
            review.id, status="completed", set_completed=True
        )

        comment = format_comment(
            findings,
            review.repo_full_name,
            review.pr_number,
        )
        await providers.git.post_review_comment(
            review.repo_full_name,
            review.pr_number,
            comment,
        )
        logger.info("Review %s completed with %d findings", review_id, len(findings))
    except Exception as exc:
        logger.exception("Review %s failed", review_id)
        try:
            repo = ReviewRepository(conn)
            await repo.update_status(
                UUID(review_id),
                status="failed",
                error_message=str(exc),
                set_completed=True,
            )
        except Exception:
            logger.exception("Failed to update review status")
        raise
    finally:
        if workspace is not None and providers is not None:
            try:
                await providers.runtime.cleanup_workspace(workspace)
            except Exception:
                logger.exception("Failed to cleanup workspace")
        await conn.close()
