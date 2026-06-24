from uuid import UUID

from app.providers.factory import build_providers_from_integration
from app.providers.protocols import ProviderBundle
from app.repositories.llm_providers import LlmProviderRepository, LlmProviderRow
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)


async def resolve_repo_integration(conn, repo_full_name: str):
    return await RepoIntegrationRepository(conn).resolve_for_repo(repo_full_name)


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


async def build_providers_for_repo(
    conn,
    repo_full_name: str,
) -> ProviderBundle:
    repo_integration = await resolve_repo_integration(conn, repo_full_name)
    if repo_integration is None:
        msg = f"No repository integration configured for {repo_full_name}"
        raise ValueError(msg)
    return build_providers_from_integration(repo_integration)


async def build_providers_for_review(
    conn,
    repo_integration_id: UUID | None,
    repo_full_name: str,
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

    providers = build_providers_from_integration(repo_integration)
    return providers, repo_integration, llm_provider
