import logging
from uuid import UUID

import asyncpg

from app.config import get_settings
from app.providers.protocols import (
    InlineComment,
    ProviderBundle,
    ReviewFinding,
    Workspace,
    WorkspaceSpec,
)
from app.repositories.reviews import ReviewRepository
from app.services.provider_resolution import build_providers_for_review
from app.services.review_format import format_summary_comment, split_findings

logger = logging.getLogger(__name__)


def _summary_findings(
    findings: list[ReviewFinding],
    posted_inline: tuple[InlineComment, ...],
) -> list[ReviewFinding]:
    """Findings for the PR summary comment (excludes successfully posted inline)."""
    posted_keys = {(c.path, c.line) for c in posted_inline}
    return [
        finding
        for finding in findings
        if not (
            finding.file_path
            and finding.line_start
            and (finding.file_path, finding.line_start) in posted_keys
        )
    ]


async def execute_review_logic(review_id: str) -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    providers: ProviderBundle | None = None
    workspace: Workspace | None = None
    try:
        repo = ReviewRepository(conn)
        review = await repo.get(UUID(review_id))
        if review is None:
            msg = f"Review not found: {review_id}"
            raise ValueError(msg)

        providers, _, _ = await build_providers_for_review(
            conn,
            review.repo_integration_id,
            review.repo_full_name,
        )

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
        await providers.git.clone_repository(
            spec,
            workspace,
            providers.runtime.command_runner(),
        )
        repo_workspace = Workspace(path=workspace.path / "repo", spec=spec)
        findings = await providers.llm.run_review(repo_workspace, pr_context)

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
        inline_comments, _ = split_findings(findings)
        posted_inline: tuple[InlineComment, ...] = ()
        if inline_comments:
            inline_result = await providers.git.post_inline_comments(
                review.repo_full_name,
                review.pr_number,
                review.head_sha,
                inline_comments,
                diff=pr_context.diff,
            )
            posted_inline = inline_result.posted
            if inline_result.skipped:
                logger.info(
                    "Review %s: %d inline comment(s) moved to summary (not in diff)",
                    review_id,
                    len(inline_result.skipped),
                )

        summary_findings = _summary_findings(findings, posted_inline)
        summary = format_summary_comment(
            summary_findings,
            review.repo_full_name,
            review.pr_number,
        )
        await providers.git.post_review_comment(
            review.repo_full_name,
            review.pr_number,
            summary,
        )

        await repo.update_status(
            review.id, status="completed", set_completed=True
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
