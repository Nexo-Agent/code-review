import logging
from pathlib import Path

from coreview_shared.agent.opencode import OpenCodeAgent
from coreview_shared.git.models import (
    InlineComment,
    PreparedReview,
)
from coreview_shared.review import ReviewFinding
from coreview_shared.schemas.review_callback import (
    ReviewCallbackError,
    ReviewCallbackGithubResult,
    ReviewCallbackResult,
)
from coreview_shared.workspace.models import WorkspaceSpec
from coreview_shared.workspace.paths import repo_base_dir

from app.config import clear_agent_settings_cache, get_agent_settings
from app.providers.factory import build_providers_from_env
from app.services.opencode_config import materialize_opencode_config
from app.services.review_callback import (
    ReviewCallbackClient,
    findings_to_callback,
    request_from_env,
    request_from_metadata,
)
from app.services.review_env import require_review_env
from app.services.review_format import format_summary_comment, split_findings

logger = logging.getLogger(__name__)


def _summary_findings(
    findings: list[ReviewFinding],
    posted_inline: tuple[InlineComment, ...],
) -> list[ReviewFinding]:
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


def _with_ci_summary(review: PreparedReview, ci_summary: str) -> PreparedReview:
    return PreparedReview(
        context=type(review.context)(
            metadata=review.context.metadata,
            diff=review.context.diff,
            ci_summary=ci_summary,
        ),
        workspace=review.workspace,
        remote_access=review.remote_access,
        provider_data=review.provider_data,
    )


async def execute_review_logic(review_id: str) -> None:
    clear_agent_settings_cache()
    infra = get_agent_settings()
    if not infra.review_id.strip():
        infra = infra.model_copy(update={"review_id": review_id})
    require_review_env(infra)

    callback = ReviewCallbackClient.from_settings(infra)
    prepared_review: PreparedReview | None = None
    providers = None
    try:
        providers = build_providers_from_env(infra)

        ci_summary = await providers.ci.get_ci_summary(
            infra.repo_full_name,
            infra.head_sha,
        )

        spec = WorkspaceSpec(
            review_id=review_id,
            repo_full_name=infra.repo_full_name,
            pr_number=infra.pr_number,
            head_sha=infra.head_sha,
        )
        repo_base = repo_base_dir(
            Path(infra.workspace_root),
            infra.git_provider,
            infra.repo_full_name,
        )
        logger.info("Review %s: preparing review workspace at %s", review_id, repo_base)
        prepared_review = await providers.git.prepare_review(spec, repo_base)
        prepared_review = _with_ci_summary(prepared_review, ci_summary)
        pr_context = prepared_review.context
        request = request_from_metadata(pr_context.metadata, infra.git_provider)

        await callback.post_event(
            callback.build_event(
                "review.started",
                review_id=review_id,
                request=request,
            )
        )

        config_path = materialize_opencode_config(infra, review_id=review_id)
        review_agent = OpenCodeAgent(
            agent=infra.opencode_agent,
            model=infra.resolved_opencode_model,
            timeout_seconds=infra.review_timeout_seconds,
            opencode_config_path=str(config_path),
            log_level=infra.opencode_log_level,
        )
        logger.info("Review %s: running LLM review", review_id)
        findings = await review_agent.run_review(
            prepared_review.workspace.workspace,
            pr_context,
        )

        logger.info(
            "Review %s: posting %d finding(s) to remote",
            review_id,
            len(findings),
        )
        inline_comments, _ = split_findings(findings)
        posted_inline: tuple[InlineComment, ...] = ()
        inline_skipped = 0
        if inline_comments:
            inline_result = await providers.git.publish_inline_comments(
                prepared_review,
                inline_comments,
            )
            posted_inline = inline_result.posted
            inline_skipped = len(inline_result.skipped)
            if inline_result.skipped:
                logger.info(
                    "Review %s: %d inline comment(s) moved to summary (not in diff)",
                    review_id,
                    inline_skipped,
                )

        summary_findings = _summary_findings(findings, posted_inline)
        summary = format_summary_comment(
            summary_findings,
            infra.repo_full_name,
            infra.pr_number,
        )
        await providers.git.publish_summary_comment(prepared_review, summary)

        await callback.post_event(
            callback.build_event(
                "review.completed",
                review_id=review_id,
                request=request,
                result=ReviewCallbackResult(
                    findings=findings_to_callback(findings),
                    github=ReviewCallbackGithubResult(
                        summary_comment_posted=True,
                        inline_comments_posted=len(posted_inline),
                        inline_comments_skipped=inline_skipped,
                    ),
                ),
            )
        )
        logger.info("Review %s completed with %d findings", review_id, len(findings))
    except Exception as exc:
        logger.exception("Review %s failed", review_id)
        try:
            await callback.post_event(
                callback.build_event(
                    "review.failed",
                    review_id=review_id,
                    request=request_from_env(infra),
                    error=ReviewCallbackError(message=str(exc)),
                )
            )
        except Exception:
            logger.exception("Failed to send review.failed callback")
        raise
    finally:
        if prepared_review is not None and providers is not None:
            try:
                await providers.git.cleanup_review(prepared_review)
            except Exception:
                logger.exception(
                    "Failed to cleanup worktree %s",
                    prepared_review.workspace.worktree_path,
                )
