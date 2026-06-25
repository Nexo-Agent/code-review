import json
import logging
from pathlib import Path
from uuid import UUID

from coreview_shared.protocols import ProviderBundle

from app.config import CodeReviewSettings, ReviewRuntimeConfig, get_code_review_settings
from app.paths import opencode_generated_config_path
from app.providers.factory import build_providers
from app.providers.opencode_config import build_opencode_config_from_llm_providers
from app.repositories.llm_providers import LlmProviderRepository, LlmProviderRow
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)

logger = logging.getLogger(__name__)


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
        return await llm_repo.get(repo_integration.llm_provider_id)
    return None


async def resolve_llm_provider_by_id(
    conn,
    llm_provider_id: UUID,
) -> LlmProviderRow | None:
    return await LlmProviderRepository(conn).get(llm_provider_id)


def build_review_runtime_config(
    repo_integration: RepoIntegrationRow,
    llm_provider: LlmProviderRow,
) -> ReviewRuntimeConfig:
    return ReviewRuntimeConfig(
        git_provider=repo_integration.git_provider,
        github_webhook_secret=repo_integration.github_webhook_secret,
        github_token=repo_integration.github_token,
        llm_provider_id=llm_provider.provider_id,
        llm_base_url=llm_provider.base_url,
        llm_api_token=llm_provider.api_token,
        llm_model=llm_provider.model,
        opencode_model=llm_provider.opencode_model,
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
    runtime = build_review_runtime_config(repo_integration, llm_provider)
    return build_providers(runtime, infra=infra)


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
    path = output_path or opencode_generated_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote OpenCode config with %d LLM provider(s)", len(providers))
    return path
