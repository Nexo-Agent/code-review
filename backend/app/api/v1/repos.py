from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.repositories.projects import ProjectRepository
from app.repositories.repo_integrations import RepoIntegrationRepository
from app.schemas.repo_integration import RepoIntegrationResponse
from app.services.repo_integrations import to_repo_integration_response

router = APIRouter()


@router.get("", response_model=list[RepoIntegrationResponse])
async def get_repo_integrations_legacy(
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> list[RepoIntegrationResponse]:
    """Legacy flat list — returns repos in projects under accessible teams."""
    if not auth.accessible_team_ids:
        return []
    project_repo = ProjectRepository(conn)
    repo_repo = RepoIntegrationRepository(conn)
    result: list[RepoIntegrationResponse] = []
    for team_id in auth.accessible_team_ids:
        projects = await project_repo.list_for_team(team_id)
        for project in projects:
            rows = await repo_repo.list_for_project(project.id)
            for row in rows:
                result.append(to_repo_integration_response(row))
    return result


@router.get("/{integration_id}", response_model=RepoIntegrationResponse)
async def get_repo_integration_legacy(
    integration_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> RepoIntegrationResponse:
    row = await RepoIntegrationRepository(conn).get(integration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    project = await ProjectRepository(conn).get(row.project_id)
    if project is None or project.team_id not in auth.accessible_team_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return to_repo_integration_response(row)
