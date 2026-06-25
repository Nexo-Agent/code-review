import json
from uuid import UUID

from coreview_shared.runtime.specs import ReviewJobRequest

from app.config import CodeReviewSettings, get_code_review_settings
from app.repositories.llm_providers import LlmProviderRow
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)
from app.repositories.reviews import ReviewRepository, ReviewRow
from app.services.provider_resolution import resolve_llm_provider


async def resolve_repo_integration_for_review(
    conn,
    *,
    repo_integration_id: UUID | None,
    repo_full_name: str,
) -> RepoIntegrationRow:
    repo_repo = RepoIntegrationRepository(conn)
    if repo_integration_id is not None:
        row = await repo_repo.get(repo_integration_id)
        if row is not None:
            return row

    row = await repo_repo.resolve_for_repo(repo_full_name)
    if row is None:
        msg = f"No repository integration configured for {repo_full_name}"
        raise ValueError(msg)
    return row


def _callback_metadata(review: ReviewRow) -> str:
    metadata: dict[str, str] = {}
    if review.delivery_id:
        metadata["delivery_id"] = review.delivery_id
    if review.repo_integration_id is not None:
        metadata["repo_integration_id"] = str(review.repo_integration_id)
    return json.dumps(metadata)


def build_agent_environment(
    *,
    review_id: str,
    review: ReviewRow,
    repo_integration: RepoIntegrationRow,
    llm_provider: LlmProviderRow,
    infra: CodeReviewSettings,
) -> dict[str, str]:
    if not infra.agent_callback_url.strip():
        msg = "NEXO_COREVIEW_AGENT_CALLBACK_URL is not configured"
        raise ValueError(msg)
    if not infra.agent_callback_secret.strip():
        msg = "NEXO_COREVIEW_AGENT_CALLBACK_SECRET is not configured"
        raise ValueError(msg)

    return {
        "NEXO_COREVIEW_REPO_FULL_NAME": review.repo_full_name,
        "NEXO_COREVIEW_PR_NUMBER": str(review.pr_number),
        "NEXO_COREVIEW_HEAD_SHA": review.head_sha,
        "NEXO_COREVIEW_GIT_PROVIDER": repo_integration.git_provider,
        "NEXO_COREVIEW_GITHUB_TOKEN": repo_integration.github_token,
        "NEXO_COREVIEW_LLM_PROVIDER_ID": llm_provider.provider_id,
        "NEXO_COREVIEW_LLM_BASE_URL": llm_provider.base_url,
        "NEXO_COREVIEW_LLM_API_TOKEN": llm_provider.api_token,
        "NEXO_COREVIEW_LLM_MODEL": llm_provider.model,
        "NEXO_COREVIEW_OPENCODE_MODEL": llm_provider.resolved_opencode_model,
        "NEXO_COREVIEW_OPENCODE_AGENT": infra.opencode_agent,
        "NEXO_COREVIEW_REVIEW_TIMEOUT_SECONDS": str(infra.review_timeout_seconds),
        "NEXO_COREVIEW_OPENCODE_LOG_LEVEL": infra.opencode_log_level,
        "NEXO_COREVIEW_WORKSPACE_ROOT": infra.workspace_root,
        "NEXO_COREVIEW_REVIEW_ID": review_id,
        "NEXO_COREVIEW_CALLBACK_URL": infra.agent_callback_url,
        "NEXO_COREVIEW_CALLBACK_SECRET": infra.agent_callback_secret,
        "NEXO_COREVIEW_CALLBACK_METADATA": _callback_metadata(review),
        "PYTHONUNBUFFERED": "1",
    }


async def prepare_review_job(
    conn,
    review_id: str,
    *,
    infra: CodeReviewSettings | None = None,
) -> ReviewJobRequest:
    infra = infra or get_code_review_settings()

    repo = ReviewRepository(conn)
    review = await repo.get(UUID(review_id))
    if review is None:
        msg = f"Review not found: {review_id}"
        raise ValueError(msg)

    repo_integration = await resolve_repo_integration_for_review(
        conn,
        repo_integration_id=review.repo_integration_id,
        repo_full_name=review.repo_full_name,
    )
    llm_provider = await resolve_llm_provider(conn, repo_integration)
    if llm_provider is None:
        msg = "No LLM provider configured"
        raise ValueError(msg)

    environment = build_agent_environment(
        review_id=review_id,
        review=review,
        repo_integration=repo_integration,
        llm_provider=llm_provider,
        infra=infra,
    )
    return ReviewJobRequest(review_id=review_id, environment=environment)
