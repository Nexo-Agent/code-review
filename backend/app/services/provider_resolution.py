import json
import logging
import os
from pathlib import Path
from uuid import UUID

from app.config import CodeReviewSettings, get_code_review_settings
from app.providers.factory import build_providers
from app.providers.opencode_config import build_opencode_config_from_llm_providers
from app.providers.protocols import ProviderBundle
from app.repositories.llm_providers import LlmProviderRepository, LlmProviderRow
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENCODE_CONFIG_PATH = Path(
    os.environ.get("NEXO_COREVIEW_OPENCODE_CONFIG_PATH", "opencode.generated.json")
)


async def resolve_repo_integration(
    conn,
    repo_full_name: str,
) -> RepoIntegrationRow | None:
    repo = RepoIntegrationRepository(conn)
    return await repo.resolve_for_repo(repo_full_name)


async def resolve_llm_provider(
    conn,
    repo_integration: RepoIntegrationRow,
) -> LlmProviderRow | None:
    llm_repo = LlmProviderRepository(conn)
    if repo_integration.llm_provider_id:
        provider = await llm_repo.get(repo_integration.llm_provider_id)
        if provider:
            return provider
    return await llm_repo.get_default()


async def resolve_llm_provider_by_id(
    conn,
    llm_provider_id: UUID,
) -> LlmProviderRow | None:
    return await LlmProviderRepository(conn).get(llm_provider_id)


def build_providers_config(
    repo_integration: RepoIntegrationRow,
    llm_provider: LlmProviderRow,
    infra: CodeReviewSettings | None = None,
) -> CodeReviewSettings:
    infra = infra or get_code_review_settings()
    return CodeReviewSettings(
        git_provider=repo_integration.git_provider,
        github_webhook_secret=repo_integration.github_webhook_secret,
        github_token=repo_integration.github_token,
        celery_broker_url=infra.celery_broker_url,
        runtime_provider=infra.runtime_provider,
        workspace_root=infra.workspace_root,
        workspace_image=infra.workspace_image,
        docker_host=infra.docker_host,
        git_image=infra.git_image or infra.workspace_image,
        mcp_server_url=infra.mcp_server_url,
        mcp_server_port=infra.mcp_server_port,
        llm_provider_id=llm_provider.provider_id,
        llm_base_url=llm_provider.base_url,
        llm_api_token=llm_provider.api_token,
        llm_model=llm_provider.model,
        opencode_agent=infra.opencode_agent,
        opencode_model=llm_provider.opencode_model,
        opencode_server_url=infra.opencode_server_url,
        opencode_server_password=infra.opencode_server_password,
        opencode_server_username=infra.opencode_server_username,
        review_timeout_seconds=infra.review_timeout_seconds,
    )


async def build_providers_for_repo(
    conn,
    repo_full_name: str,
    infra: CodeReviewSettings | None = None,
) -> ProviderBundle:
    repo_integration = await resolve_repo_integration(conn, repo_full_name)
    if repo_integration is None:
        msg = f"No repository integration configured for {repo_full_name}"
        raise ValueError(msg)
    llm_provider = await resolve_llm_provider(conn, repo_integration)
    if llm_provider is None:
        msg = "No LLM provider configured"
        raise ValueError(msg)
    cfg = build_providers_config(repo_integration, llm_provider, infra)
    return build_providers(cfg)


async def build_providers_for_review(
    conn,
    repo_integration_id: UUID | None,
    repo_full_name: str,
    infra: CodeReviewSettings | None = None,
) -> tuple[ProviderBundle, RepoIntegrationRow, LlmProviderRow]:
    repo_repo = RepoIntegrationRepository(conn)
    if repo_integration_id:
        repo_integration = await repo_repo.get(repo_integration_id)
    else:
        repo_integration = None

    if repo_integration is None:
        repo_integration = await repo_repo.resolve_for_repo(repo_full_name)

    if repo_integration is None:
        msg = f"No repository integration configured for {repo_full_name}"
        raise ValueError(msg)

    llm_provider = await resolve_llm_provider(conn, repo_integration)
    if llm_provider is None:
        msg = "No LLM provider configured"
        raise ValueError(msg)

    cfg = build_providers_config(repo_integration, llm_provider, infra)
    return build_providers(cfg), repo_integration, llm_provider


async def sync_opencode_config_from_db(
    conn,
    output_path: Path | None = None,
    infra: CodeReviewSettings | None = None,
) -> Path:
    infra = infra or get_code_review_settings()
    llm_repo = LlmProviderRepository(conn)
    providers = await llm_repo.list_all()
    default = await llm_repo.get_default()
    config = build_opencode_config_from_llm_providers(providers, default, infra)
    path = output_path or DEFAULT_OPENCODE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote OpenCode config with %d LLM provider(s)", len(providers))
    return path
