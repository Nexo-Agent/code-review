import logging
from uuid import UUID

from coreview_shared.providers.git.azure_devops import parse_repo_full_name

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


def _infer_ado_org_project(git_provider: str, repo_full_name: str) -> tuple[str, str]:
    if git_provider != "azure-devops":
        return "", ""
    trimmed = repo_full_name.strip()
    if not trimmed:
        return "", ""
    organization, project, _repo = parse_repo_full_name(trimmed)
    return organization, project


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
        system_prompt=row.system_prompt,
        enabled=row.enabled,
        github_webhook_secret_configured=bool(row.github_webhook_secret),
        github_token_configured=bool(row.github_token),
        ado_organization=row.ado_organization,
        ado_project=row.ado_project,
        ado_pat_configured=bool(row.ado_pat),
        ado_webhook_configured=bool(
            row.ado_webhook_username and row.ado_webhook_password
        ),
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
    ado_organization, ado_project = _infer_ado_org_project(
        payload.git_provider,
        payload.repo_full_name,
    )
    row = await repo.create(
        name=payload.name or _default_repo_name(payload.repo_full_name),
        git_provider=payload.git_provider,
        repo_full_name=payload.repo_full_name,
        github_webhook_secret=payload.github_webhook_secret,
        github_token=payload.github_token,
        llm_provider_id=payload.llm_provider_id,
        system_prompt=payload.system_prompt,
        enabled=payload.enabled,
        ado_organization=ado_organization,
        ado_project=ado_project,
        ado_pat=payload.ado_pat,
        ado_webhook_username=payload.ado_webhook_username,
        ado_webhook_password=payload.ado_webhook_password,
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
    current = await repo.get(integration_id)
    if current is None:
        msg = "repo integration not found"
        raise ValueError(msg)
    data = payload.model_dump(exclude_unset=True)
    git_provider = data.get("git_provider", current.git_provider)
    repo_full_name = data.get("repo_full_name", current.repo_full_name)
    ado_organization, ado_project = _infer_ado_org_project(
        git_provider,
        repo_full_name,
    )
    data["ado_organization"] = ado_organization
    data["ado_project"] = ado_project
    clear_webhook_secret = (
        "github_webhook_secret" in data and data["github_webhook_secret"] == ""
    )
    clear_github_token = "github_token" in data and data["github_token"] == ""
    clear_ado_pat = "ado_pat" in data and data["ado_pat"] == ""
    clear_ado_webhook_password = (
        "ado_webhook_password" in data and data["ado_webhook_password"] == ""
    )
    row = await repo.update(
        integration_id,
        name=data.get("name"),
        git_provider=data.get("git_provider"),
        repo_full_name=data.get("repo_full_name"),
        github_webhook_secret=data.get("github_webhook_secret"),
        github_token=data.get("github_token"),
        llm_provider_id=data.get("llm_provider_id"),
        clear_llm_provider_id=data.get("clear_llm_provider_id", False),
        system_prompt=data.get("system_prompt"),
        enabled=data.get("enabled"),
        clear_webhook_secret=clear_webhook_secret,
        clear_github_token=clear_github_token,
        ado_organization=data.get("ado_organization"),
        ado_project=data.get("ado_project"),
        ado_pat=data.get("ado_pat"),
        ado_webhook_username=data.get("ado_webhook_username"),
        ado_webhook_password=data.get("ado_webhook_password"),
        clear_ado_pat=clear_ado_pat,
        clear_ado_webhook_password=clear_ado_webhook_password,
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
