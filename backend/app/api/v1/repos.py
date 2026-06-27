from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.pagination import PaginationParams
from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.repositories.repo_integrations import RepoIntegrationRepository
from app.schemas.repo_integration import (
    RepoIntegrationListResponse,
    RepoIntegrationResponse,
)
from app.services.repo_integrations import (
    list_repo_integrations_for_teams_paginated,
    to_repo_integration_response,
)

router = APIRouter()


@router.get("", response_model=RepoIntegrationListResponse)
async def get_repo_integrations_legacy(
    q: str | None = Query(None, max_length=200),
    team_id: list[UUID] = Query(default=[]),
    enabled: bool | None = Query(None),
    git_provider: str | None = Query(None, max_length=32),
    pagination: PaginationParams = Depends(),
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> RepoIntegrationListResponse:
    """Legacy flat list — returns repos in accessible teams."""
    if not auth.accessible_team_ids:
        return RepoIntegrationListResponse(items=[], total=0)
    org_result = await list_repo_integrations_for_teams_paginated(
        conn,
        auth.accessible_team_ids,
        search=q,
        filter_team_ids=team_id or None,
        enabled=enabled,
        git_provider=git_provider,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return RepoIntegrationListResponse(items=org_result.items, total=org_result.total)


@router.get("/{integration_id}", response_model=RepoIntegrationResponse)
async def get_repo_integration_legacy(
    integration_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> RepoIntegrationResponse:
    row = await RepoIntegrationRepository(conn).get(integration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if row.team_id not in auth.accessible_team_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return await to_repo_integration_response(conn, row)
