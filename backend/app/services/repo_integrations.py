import logging
from uuid import UUID

from coreview_shared.providers.git.azure_devops import parse_repo_full_name

from app.repositories.projects import ProjectRepository
from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)
from app.repositories.teams import TeamRepository
from app.schemas.repo_integration import (
    OrgRepositoryResponse,
    RepoIntegrationCreate,
    RepoIntegrationResponse,
    RepoIntegrationUpdate,
    TeamRepositoryResponse,
)
from app.services.projects import _llm_provider_name, _validate_llm_provider_for_org

logger = logging.getLogger(__name__)


def _infer_ado_org_project(git_provider: str, repo_full_name: str) -> tuple[str, str]:
    if git_provider != "azure-devops":
        return "", ""
    trimmed = repo_full_name.strip()
    if not trimmed:
        return "", ""
    organization, project, _repo = parse_repo_full_name(trimmed)
    return organization, project


def build_webhook_url(integration: RepoIntegrationRow) -> str:
    provider_path = (
        "azure-devops" if integration.git_provider == "azure-devops" else "github"
    )
    return f"/api/v1/webhooks/{provider_path}/{integration.id}"


async def to_repo_integration_response(
    conn,
    row: RepoIntegrationRow,
) -> RepoIntegrationResponse:
    llm_name = await _llm_provider_name(conn, row.llm_provider_id)
    return RepoIntegrationResponse(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        git_provider=row.git_provider,
        repo_full_name=row.repo_full_name,
        llm_provider_id=row.llm_provider_id,
        llm_provider_name=llm_name,
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
        webhook_url=build_webhook_url(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_repo_integrations_for_project(
    conn,
    project_id: UUID,
) -> list[RepoIntegrationResponse]:
    project = await ProjectRepository(conn).get(project_id)
    if project is None:
        msg = "project not found"
        raise ValueError(msg)
    rows = await RepoIntegrationRepository(conn).list_for_project(project_id)
    return [await to_repo_integration_response(conn, row) for row in rows]


async def list_repo_integrations_for_team(
    conn,
    team_id: UUID,
) -> list[TeamRepositoryResponse]:
    team = await TeamRepository(conn).get(team_id)
    if team is None:
        msg = "team not found"
        raise ValueError(msg)
    rows = await RepoIntegrationRepository(conn).list_for_team(team_id)
    results: list[TeamRepositoryResponse] = []
    for row, project_name in rows:
        base = await to_repo_integration_response(conn, row)
        results.append(
            TeamRepositoryResponse(
                **base.model_dump(),
                project_name=project_name,
            )
        )
    return results


async def list_repo_integrations_for_teams(
    conn,
    team_ids: list[UUID],
) -> list[OrgRepositoryResponse]:
    if not team_ids:
        return []
    rows = await RepoIntegrationRepository(conn).list_for_teams(team_ids)
    results: list[OrgRepositoryResponse] = []
    for row, project_name, team_id, team_name in rows:
        base = await to_repo_integration_response(conn, row)
        results.append(
            OrgRepositoryResponse(
                **base.model_dump(),
                project_name=project_name,
                team_id=team_id,
                team_name=team_name,
            )
        )
    return results


async def get_repo_integration(
    conn,
    integration_id: UUID,
) -> RepoIntegrationResponse:
    row = await RepoIntegrationRepository(conn).get(integration_id)
    if row is None:
        msg = "repo integration not found"
        raise ValueError(msg)
    return await to_repo_integration_response(conn, row)


async def create_repo_integration(
    conn,
    project_id: UUID,
    payload: RepoIntegrationCreate,
) -> RepoIntegrationResponse:
    project = await ProjectRepository(conn).get(project_id)
    if project is None:
        msg = "project not found"
        raise ValueError(msg)
    await _validate_llm_provider_for_org(conn, payload.llm_provider_id)
    repo = RepoIntegrationRepository(conn)
    ado_organization, ado_project = _infer_ado_org_project(
        payload.git_provider,
        payload.repo_full_name,
    )
    row = await repo.create(
        project_id=project_id,
        name=payload.name or _default_repo_name(payload.repo_full_name),
        git_provider=payload.git_provider,
        repo_full_name=payload.repo_full_name,
        github_webhook_secret=payload.github_webhook_secret,
        github_token=payload.github_token,
        system_prompt=payload.system_prompt,
        enabled=payload.enabled,
        ado_organization=ado_organization,
        ado_project=ado_project,
        ado_pat=payload.ado_pat,
        ado_webhook_username=payload.ado_webhook_username,
        ado_webhook_password=payload.ado_webhook_password,
        llm_provider_id=payload.llm_provider_id,
    )
    logger.info("Created repo integration %s", row.repo_full_name or "*")
    return await to_repo_integration_response(conn, row)


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
    if payload.llm_provider_id is not None:
        await _validate_llm_provider_for_org(conn, payload.llm_provider_id)
    git_provider = data.get("git_provider", current.git_provider)
    repo_full_name = data.get("repo_full_name", current.repo_full_name)
    ado_organization, ado_project = _infer_ado_org_project(
        git_provider,
        repo_full_name,
    )
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
        system_prompt=data.get("system_prompt"),
        enabled=data.get("enabled"),
        clear_webhook_secret=clear_webhook_secret,
        clear_github_token=clear_github_token,
        ado_organization=ado_organization,
        ado_project=ado_project,
        ado_pat=data.get("ado_pat"),
        ado_webhook_username=data.get("ado_webhook_username"),
        ado_webhook_password=data.get("ado_webhook_password"),
        clear_ado_pat=clear_ado_pat,
        clear_ado_webhook_password=clear_ado_webhook_password,
        llm_provider_id=data.get("llm_provider_id"),
        clear_llm_provider_id=payload.clear_llm_provider_id,
    )
    logger.info("Updated repo integration %s", row.repo_full_name or "*")
    return await to_repo_integration_response(conn, row)


async def delete_repo_integration(conn, integration_id: UUID) -> None:
    await RepoIntegrationRepository(conn).delete(integration_id)
    logger.info("Deleted repo integration %s", integration_id)


def _default_repo_name(repo_full_name: str) -> str:
    return repo_full_name.strip() or "All repositories"
