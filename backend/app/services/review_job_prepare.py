import json
from uuid import UUID

from coreview_shared.runtime.specs import ReviewJobRequest

from app.config import CodeReviewSettings, get_code_review_settings
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)
from app.repositories.reviews import ReviewRepository, ReviewRow
from app.services.provider_resolution import resolve_llm_provider_for_repo


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
    llm_provider,
    infra: CodeReviewSettings,
) -> dict[str, str]:
    if not infra.agent_callback_url.strip():
        msg = "COGITO_REVIEW_AGENT_CALLBACK_URL is not configured"
        raise ValueError(msg)
    if not infra.agent_callback_secret.strip():
        msg = "COGITO_REVIEW_AGENT_CALLBACK_SECRET is not configured"
        raise ValueError(msg)

    env: dict[str, str] = {
        "COGITO_REVIEW_REPO_FULL_NAME": review.repo_full_name,
        "COGITO_REVIEW_PR_NUMBER": str(review.pr_number),
        "COGITO_REVIEW_HEAD_SHA": review.head_sha,
        "COGITO_REVIEW_GIT_PROVIDER": repo_integration.git_provider,
        "COGITO_REVIEW_GITHUB_TOKEN": repo_integration.github_token,
        "COGITO_REVIEW_LLM_PROVIDER_ID": llm_provider.provider_id,
        "COGITO_REVIEW_LLM_BASE_URL": llm_provider.base_url,
        "COGITO_REVIEW_LLM_API_TOKEN": llm_provider.api_token,
        "COGITO_REVIEW_LLM_MODEL": llm_provider.model,
        "COGITO_REVIEW_OPENCODE_MODEL": llm_provider.resolved_opencode_model,
        "COGITO_REVIEW_OPENCODE_AGENT": infra.opencode_agent,
        "COGITO_REVIEW_REVIEW_TIMEOUT_SECONDS": str(infra.review_timeout_seconds),
        "COGITO_REVIEW_OPENCODE_LOG_LEVEL": infra.opencode_log_level,
        "COGITO_REVIEW_WORKSPACE_ROOT": infra.workspace_root,
        "COGITO_REVIEW_REVIEW_ID": review_id,
        "COGITO_REVIEW_CALLBACK_URL": infra.agent_callback_url,
        "COGITO_REVIEW_CALLBACK_SECRET": infra.agent_callback_secret,
        "COGITO_REVIEW_CALLBACK_METADATA": _callback_metadata(review),
        "PYTHONUNBUFFERED": "1",
    }
    if repo_integration.system_prompt.strip():
        env["COGITO_REVIEW_SYSTEM_PROMPT"] = repo_integration.system_prompt
    if repo_integration.git_provider == "azure-devops":
        env["COGITO_REVIEW_ADO_ORGANIZATION"] = repo_integration.ado_organization
        env["COGITO_REVIEW_ADO_PROJECT"] = repo_integration.ado_project
        env["COGITO_REVIEW_ADO_PAT"] = repo_integration.ado_pat
    if repo_integration.git_provider == "gitlab":
        env["COGITO_REVIEW_GITLAB_BASE_URL"] = repo_integration.gitlab_base_url
        env["COGITO_REVIEW_GITLAB_TOKEN"] = repo_integration.gitlab_token
    return env


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
    llm_provider = await resolve_llm_provider_for_repo(conn, repo_integration)
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
