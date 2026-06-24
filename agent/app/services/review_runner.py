import logging
import shutil
from pathlib import Path

from app.config import clear_agent_settings_cache, get_agent_settings
from app.providers.factory import build_providers_from_env
from app.providers.llm.opencode import OpenCodeLLMProvider
from app.providers.protocols import (
    InlineComment,
    ReviewFinding,
    Workspace,
    WorkspaceSpec,
)
from app.providers.runtime.command_runner import LocalCommandRunner
from app.schemas.review_callback import (
    ReviewCallbackError,
    ReviewCallbackGithubResult,
    ReviewCallbackResult,
)
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


async def execute_review_logic(review_id: str) -> None:
    clear_agent_settings_cache()
    infra = get_agent_settings()
    if not infra.review_id.strip():
        infra = infra.model_copy(update={"review_id": review_id})
    require_review_env(infra)

    callback = ReviewCallbackClient.from_settings(infra)
    workspace_root: Path | None = None
    try:
        providers = build_providers_from_env(infra)

        await callback.post_event(
            callback.build_event(
                "review.started",
                review_id=review_id,
                request=request_from_env(infra),
            )
        )
        logger.info("Review %s: fetching PR context", review_id)

        pr_context = await providers.git.fetch_pr_context(
            infra.repo_full_name,
            infra.pr_number,
            infra.head_sha,
        )
        ci_summary = await providers.ci.get_ci_summary(
            infra.repo_full_name,
            infra.head_sha,
        )
        pr_context = type(pr_context)(
            metadata=pr_context.metadata,
            diff=pr_context.diff,
            ci_summary=ci_summary,
        )
        request = request_from_metadata(pr_context.metadata, infra.git_provider)

        workspace_root = Path(infra.workspace_root) / review_id
        workspace_root.mkdir(parents=True, exist_ok=True)
        spec = WorkspaceSpec(
            review_id=review_id,
            repo_full_name=infra.repo_full_name,
            pr_number=infra.pr_number,
            head_sha=infra.head_sha,
        )
        workspace = Workspace(path=workspace_root, spec=spec)
        logger.info("Review %s: cloning repository", review_id)
        await providers.git.clone_repository(spec, workspace, LocalCommandRunner())

        config_path = materialize_opencode_config(infra, review_id=review_id)
        llm = OpenCodeLLMProvider(
            agent=infra.opencode_agent,
            model=infra.resolved_opencode_model,
            timeout_seconds=infra.review_timeout_seconds,
            opencode_config_path=str(config_path),
            log_level=infra.opencode_log_level,
        )
        repo_workspace = Workspace(path=workspace_root / "repo", spec=spec)
        logger.info("Review %s: running LLM review", review_id)
        findings = await llm.run_review(repo_workspace, pr_context)

        logger.info(
            "Review %s: posting %d finding(s) to GitHub", review_id, len(findings)
        )
        inline_comments, _ = split_findings(findings)
        posted_inline: tuple[InlineComment, ...] = ()
        inline_skipped = 0
        if inline_comments:
            inline_result = await providers.git.post_inline_comments(
                infra.repo_full_name,
                infra.pr_number,
                infra.head_sha,
                inline_comments,
                diff=pr_context.diff,
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
        await providers.git.post_review_comment(
            infra.repo_full_name,
            infra.pr_number,
            summary,
        )

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
        if workspace_root is not None:
            try:
                shutil.rmtree(workspace_root, ignore_errors=True)
            except Exception:
                logger.exception("Failed to cleanup workspace")
