import logging
from uuid import UUID

from app.repositories.llm_providers import LlmProviderRepository
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)
from app.schemas.repo_integration import (
    RepoIntegrationCreate,
    RepoIntegrationResponse,
    RepoIntegrationUpdate,
)
from app.services.provider_resolution import sync_opencode_config_from_db

logger = logging.getLogger(__name__)


async def _llm_provider_name(conn, llm_provider_id: UUID | None) -> str | None:
    if llm_provider_id is None:
        return None
    row = await LlmProviderRepository(conn).get(llm_provider_id)
    return row.name if row else None


def to_repo_integration_response(
    row: RepoIntegrationRow,
    llm_provider_name: str | None,
) -> RepoIntegrationResponse:
    return RepoIntegrationResponse(
        id=row.id,
        name=row.name,
        git_provider=row.git_provider,
        repo_full_name=row.repo_full_name,
        llm_provider_id=row.llm_provider_id,
        llm_provider_name=llm_provider_name,
        enabled=row.enabled,
        github_webhook_secret_configured=bool(row.github_webhook_secret),
        github_token_configured=bool(row.github_token),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_repo_integrations(conn) -> list[RepoIntegrationResponse]:
    repo = RepoIntegrationRepository(conn)
    rows = await repo.list_all()
    result: list[RepoIntegrationResponse] = []
    for row in rows:
        name = await _llm_provider_name(conn, row.llm_provider_id)
        result.append(to_repo_integration_response(row, name))
    return result


async def create_repo_integration(
    conn,
    payload: RepoIntegrationCreate,
) -> RepoIntegrationResponse:
    repo = RepoIntegrationRepository(conn)
    row = await repo.create(
        name=payload.name or _default_repo_name(payload.repo_full_name),
        git_provider=payload.git_provider,
        repo_full_name=payload.repo_full_name,
        github_webhook_secret=payload.github_webhook_secret,
        github_token=payload.github_token,
        llm_provider_id=payload.llm_provider_id,
        enabled=payload.enabled,
    )
    await sync_opencode_config_from_db(conn)
    llm_name = await _llm_provider_name(conn, row.llm_provider_id)
    logger.info("Created repo integration %s", row.repo_full_name or "*")
    return to_repo_integration_response(row, llm_name)


async def update_repo_integration(
    conn,
    integration_id: UUID,
    payload: RepoIntegrationUpdate,
) -> RepoIntegrationResponse:
    repo = RepoIntegrationRepository(conn)
    data = payload.model_dump(exclude_unset=True)
    clear_webhook_secret = (
        "github_webhook_secret" in data and data["github_webhook_secret"] == ""
    )
    clear_github_token = "github_token" in data and data["github_token"] == ""
    row = await repo.update(
        integration_id,
        name=data.get("name"),
        git_provider=data.get("git_provider"),
        repo_full_name=data.get("repo_full_name"),
        github_webhook_secret=data.get("github_webhook_secret"),
        github_token=data.get("github_token"),
        llm_provider_id=data.get("llm_provider_id"),
        clear_llm_provider_id=data.get("clear_llm_provider_id", False),
        enabled=data.get("enabled"),
        clear_webhook_secret=clear_webhook_secret,
        clear_github_token=clear_github_token,
    )
    await sync_opencode_config_from_db(conn)
    llm_name = await _llm_provider_name(conn, row.llm_provider_id)
    logger.info("Updated repo integration %s", row.repo_full_name or "*")
    return to_repo_integration_response(row, llm_name)


async def delete_repo_integration(conn, integration_id: UUID) -> None:
    await RepoIntegrationRepository(conn).delete(integration_id)
    logger.info("Deleted repo integration %s", integration_id)


def _default_repo_name(repo_full_name: str) -> str:
    return repo_full_name.strip() or "All repositories"
