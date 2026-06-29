import json
from uuid import UUID

from coreview_shared.runtime.specs import ReviewJobRequest
from coreview_shared.schemas.execution_contracts import (
    CallbackConfig,
    CredentialRefs,
    ExecutionConfig,
    ReviewContext,
    ReviewExecutionRequest,
    RuntimeMetadata,
    SecretRef,
)

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
    if repo_integration.git_provider == "bitbucket":
        env["COGITO_REVIEW_BITBUCKET_TOKEN"] = repo_integration.bitbucket_token
    if repo_integration.git_provider == "bitbucket-dc":
        env["COGITO_REVIEW_BITBUCKET_DC_BASE_URL"] = (
            repo_integration.bitbucket_dc_base_url
        )
        env["COGITO_REVIEW_BITBUCKET_DC_TOKEN"] = repo_integration.bitbucket_dc_token
    return env


def _secret_env_from_integration(
    *,
    review: ReviewRow,
    repo_integration: RepoIntegrationRow,
    llm_provider,
    infra: CodeReviewSettings,
) -> dict[str, str]:
    env = build_agent_environment(
        review_id=str(review.id),
        review=review,
        repo_integration=repo_integration,
        llm_provider=llm_provider,
        infra=infra,
    )
    secret_keys = {
        "COGITO_REVIEW_GITHUB_TOKEN",
        "COGITO_REVIEW_GITLAB_TOKEN",
        "COGITO_REVIEW_GITLAB_BASE_URL",
        "COGITO_REVIEW_BITBUCKET_TOKEN",
        "COGITO_REVIEW_BITBUCKET_DC_TOKEN",
        "COGITO_REVIEW_BITBUCKET_DC_BASE_URL",
        "COGITO_REVIEW_ADO_PAT",
        "COGITO_REVIEW_ADO_ORGANIZATION",
        "COGITO_REVIEW_ADO_PROJECT",
        "COGITO_REVIEW_LLM_API_TOKEN",
        "COGITO_REVIEW_CALLBACK_SECRET",
    }
    return {k: v for k, v in env.items() if k in secret_keys and v}


def build_review_execution_request(
    *,
    review_id: str,
    review: ReviewRow,
    repo_integration: RepoIntegrationRow,
    llm_provider,
    infra: CodeReviewSettings,
) -> ReviewExecutionRequest:
    namespace = infra.k8s_run_namespace or infra.k8s_namespace
    git_secret = SecretRef(
        name=f"review-{review_id}-git",
        key="credentials",
        namespace=namespace,
    )
    llm_secret = SecretRef(
        name=f"review-{review_id}-llm",
        key="credentials",
        namespace=namespace,
    )
    return ReviewExecutionRequest(
        review_id=review_id,
        review=ReviewContext(
            repo_full_name=review.repo_full_name,
            pr_number=review.pr_number,
            head_sha=review.head_sha,
            git_provider=repo_integration.git_provider,
        ),
        callback=CallbackConfig(
            url=infra.agent_callback_url,
            secret_ref=SecretRef(
                name="review-callback",
                key="secret",
                namespace=namespace,
            ),
            metadata=json.loads(_callback_metadata(review) or "{}"),
        ),
        config=ExecutionConfig(
            workspace_root=infra.workspace_root,
            opencode_agent=infra.opencode_agent,
            opencode_log_level=infra.opencode_log_level,
            review_timeout_seconds=infra.review_timeout_seconds,
            system_prompt=repo_integration.system_prompt,
            llm_provider_id=llm_provider.provider_id,
            llm_base_url=llm_provider.base_url,
            llm_model=llm_provider.model,
            opencode_model=llm_provider.resolved_opencode_model,
        ),
        credentials=CredentialRefs(
            git_credential_ref=git_secret,
            llm_credential_ref=llm_secret,
        ),
        runtime_metadata=RuntimeMetadata(
            installation_ref=infra.k8s_installation_ref,
            runtime_policy_ref=infra.k8s_runtime_policy_ref,
            scaling_policy_ref=infra.k8s_scaling_policy_ref,
            namespace=namespace,
        ),
        resolved_secret_env=_secret_env_from_integration(
            review=review,
            repo_integration=repo_integration,
            llm_provider=llm_provider,
            infra=infra,
        ),
    )


async def prepare_review_execution(
    conn,
    review_id: str,
    *,
    infra: CodeReviewSettings | None = None,
) -> ReviewExecutionRequest:
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

    return build_review_execution_request(
        review_id=review_id,
        review=review,
        repo_integration=repo_integration,
        llm_provider=llm_provider,
        infra=infra,
    )


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
