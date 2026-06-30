from __future__ import annotations

from pathlib import Path

from coreview_shared.agent.models import OpenCodeRunConfig, ReviewAgentKind
from coreview_shared.git.models import PreparedReview
from coreview_shared.schemas.review_callback import ReviewCallbackRequest
from coreview_shared.workspace.models import WorkspaceSpec
from coreview_shared.workspace.paths import repo_base_dir

from app.config import AgentSettings, get_agent_settings
from app.providers.factory import build_providers_from_env
from app.services.models import ReviewRunContext

_BASE_REQUIRED_STRING_FIELDS = (
    "review_id",
    "repo_full_name",
    "head_sha",
    "llm_provider_id",
    "llm_base_url",
    "llm_api_token",
    "llm_model",
    "callback_url",
    "callback_secret",
)


def _request_from_env(settings: AgentSettings) -> ReviewCallbackRequest:
    return ReviewCallbackRequest(
        git_provider=settings.git_provider,
        repo_full_name=settings.repo_full_name,
        pr_number=settings.pr_number,
        head_sha=settings.head_sha,
    )


def _request_from_metadata(
    review: PreparedReview,
    git_provider: str,
) -> ReviewCallbackRequest:
    metadata = review.context.metadata
    return ReviewCallbackRequest(
        git_provider=git_provider,
        repo_full_name=metadata.repo_full_name,
        pr_number=metadata.pr_number,
        head_sha=metadata.head_sha,
        base_sha=metadata.base_sha,
        head_ref=metadata.head_ref,
        base_ref=metadata.base_ref,
        pr_title=metadata.title,
        pr_url=metadata.html_url,
        pr_author=metadata.author,
    )


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


def require_review_env(settings: AgentSettings) -> None:
    missing: list[str] = []
    required_fields = list(_BASE_REQUIRED_STRING_FIELDS)
    if settings.git_provider == "azure-devops":
        required_fields.extend(["ado_organization", "ado_project", "ado_pat"])
    elif settings.git_provider == "gitlab":
        required_fields.append("gitlab_token")
    elif settings.git_provider == "bitbucket-dc":
        required_fields.extend(["bitbucket_dc_base_url", "bitbucket_dc_token"])
    elif settings.git_provider == "bitbucket":
        required_fields.append("bitbucket_token")
    else:
        required_fields.append("github_token")

    for field in required_fields:
        value = getattr(settings, field, "")
        if not str(value).strip():
            missing.append(f"COGITO_REVIEW_{field.upper()}")

    if not settings.resolved_opencode_model:
        missing.append("COGITO_REVIEW_OPENCODE_MODEL (or LLM provider + model)")

    if settings.pr_number <= 0:
        missing.append("COGITO_REVIEW_PR_NUMBER")

    if missing:
        msg = f"Missing required review environment: {', '.join(missing)}"
        raise ValueError(msg)


def _build_agent_config(settings: AgentSettings, review_id: str) -> OpenCodeRunConfig:
    if settings.agent_kind is not ReviewAgentKind.OPENCODE:
        msg = f"Review agent kind '{settings.agent_kind}' is not implemented yet"
        raise NotImplementedError(msg)
    return OpenCodeRunConfig(
        kind=settings.agent_kind,
        review_id=review_id,
        agent=settings.opencode_agent,
        model=settings.resolved_opencode_model,
        timeout_seconds=settings.review_timeout_seconds,
        log_level=settings.opencode_log_level,
        llm_provider_id=settings.llm_provider_id,
        llm_base_url=settings.llm_base_url,
        llm_api_token=settings.llm_api_token,
        llm_model=settings.llm_model,
        system_prompt=settings.system_prompt,
    )


async def build_review_context(
    review_id: str,
    settings: AgentSettings | None = None,
) -> ReviewRunContext:
    infra = settings or get_agent_settings()
    require_review_env(infra)
    providers = build_providers_from_env(infra)
    context = ReviewRunContext(
        review_id=review_id,
        settings=infra,
        providers=providers,
        callback_request=_request_from_env(infra),
        agent_kind=infra.agent_kind,
        agent_config=_build_agent_config(infra, review_id),
    )

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
    prepared_review = await providers.git.prepare_review(spec, repo_base)
    prepared_review = _with_ci_summary(prepared_review, ci_summary)
    context.prepared_review = prepared_review
    context.callback_request = _request_from_metadata(
        prepared_review,
        infra.git_provider,
    )
    return context


async def cleanup_review_context(context: ReviewRunContext) -> None:
    if context.prepared_review is not None:
        await context.providers.git.cleanup_review(context.prepared_review)
