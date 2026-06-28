import logging
from uuid import UUID

from coreview_shared.providers.git.azure_devops import parse_repo_full_name

from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)
from app.repositories.teams import TeamRepository
from app.schemas.repo_integration import (
    OrgRepositoryListResponse,
    OrgRepositoryResponse,
    RepoIntegrationCreate,
    RepoIntegrationListResponse,
    RepoIntegrationResponse,
    RepoIntegrationUpdate,
)
from app.services.llm_validation import llm_provider_name, validate_llm_provider_for_org

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
    provider_paths = {
        "azure-devops": "azure-devops",
        "gitlab": "gitlab",
    }
    provider_path = provider_paths.get(integration.git_provider, "github")
    return f"/api/v1/webhooks/{provider_path}/{integration.id}"


async def to_repo_integration_response(
    conn,
    row: RepoIntegrationRow,
) -> RepoIntegrationResponse:
    llm_name = await llm_provider_name(conn, row.llm_provider_id)
    return RepoIntegrationResponse(
        id=row.id,
        team_id=row.team_id,
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
        gitlab_base_url=row.gitlab_base_url,
        gitlab_token_configured=bool(row.gitlab_token),
        gitlab_webhook_secret_configured=bool(row.gitlab_webhook_secret),
        webhook_url=build_webhook_url(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_repo_integrations_for_team_paginated(
    conn,
    team_id: UUID,
    *,
    search: str | None,
    enabled: bool | None,
    limit: int,
    offset: int,
) -> RepoIntegrationListResponse:
    team = await TeamRepository(conn).get(team_id)
    if team is None:
        msg = "team not found"
        raise ValueError(msg)
    repo = RepoIntegrationRepository(conn)
    query = (search or "").strip()
    rows = await repo.list_for_team_paginated(
        team_id,
        search=query,
        enabled=enabled,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_for_team(
        team_id,
        search=query,
        enabled=enabled,
    )
    items = [await to_repo_integration_response(conn, row) for row in rows]
    return RepoIntegrationListResponse(items=items, total=total)


async def list_repo_integrations_for_teams_paginated(
    conn,
    team_ids: list[UUID],
    *,
    search: str | None,
    filter_team_ids: list[UUID] | None,
    enabled: bool | None,
    git_provider: str | None,
    limit: int,
    offset: int,
) -> OrgRepositoryListResponse:
    if not team_ids:
        return OrgRepositoryListResponse(items=[], total=0)
    repo = RepoIntegrationRepository(conn)
    query = (search or "").strip()
    rows = await repo.list_for_teams_paginated(
        team_ids,
        search=query,
        filter_team_ids=filter_team_ids,
        enabled=enabled,
        git_provider=git_provider,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_for_teams(
        team_ids,
        search=query,
        filter_team_ids=filter_team_ids,
        enabled=enabled,
        git_provider=git_provider,
    )
    results: list[OrgRepositoryResponse] = []
    for row, _team_id, team_name in rows:
        base = await to_repo_integration_response(conn, row)
        results.append(
            OrgRepositoryResponse(
                **base.model_dump(),
                team_name=team_name,
            )
        )
    return OrgRepositoryListResponse(items=results, total=total)


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
    team_id: UUID,
    payload: RepoIntegrationCreate,
) -> RepoIntegrationResponse:
    team = await TeamRepository(conn).get(team_id)
    if team is None:
        msg = "team not found"
        raise ValueError(msg)
    await validate_llm_provider_for_org(conn, payload.llm_provider_id)
    repo = RepoIntegrationRepository(conn)
    ado_organization, ado_project = _infer_ado_org_project(
        payload.git_provider,
        payload.repo_full_name,
    )
    row = await repo.create(
        team_id=team_id,
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
        gitlab_base_url=payload.gitlab_base_url,
        gitlab_token=payload.gitlab_token,
        gitlab_webhook_secret=payload.gitlab_webhook_secret,
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
        await validate_llm_provider_for_org(conn, payload.llm_provider_id)
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
    clear_gitlab_token = "gitlab_token" in data and data["gitlab_token"] == ""
    clear_gitlab_webhook_secret = (
        "gitlab_webhook_secret" in data and data["gitlab_webhook_secret"] == ""
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
        gitlab_base_url=data.get("gitlab_base_url"),
        gitlab_token=data.get("gitlab_token"),
        gitlab_webhook_secret=data.get("gitlab_webhook_secret"),
        clear_gitlab_token=clear_gitlab_token,
        clear_gitlab_webhook_secret=clear_gitlab_webhook_secret,
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
