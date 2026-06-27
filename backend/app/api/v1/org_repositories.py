from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query

from app.api.pagination import PaginationParams
from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.schemas.repo_integration import OrgRepositoryListResponse
from app.services.repo_integrations import list_repo_integrations_for_teams_paginated

router = APIRouter()


@router.get("", response_model=OrgRepositoryListResponse)
async def get_org_repositories(
    q: str | None = Query(None, max_length=200),
    team_id: list[UUID] = Query(default=[]),
    enabled: bool | None = Query(None),
    git_provider: str | None = Query(None, max_length=32),
    pagination: PaginationParams = Depends(),
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> OrgRepositoryListResponse:
    if not auth.accessible_team_ids:
        return OrgRepositoryListResponse(items=[], total=0)
    return await list_repo_integrations_for_teams_paginated(
        conn,
        auth.accessible_team_ids,
        search=q,
        filter_team_ids=team_id or None,
        enabled=enabled,
        git_provider=git_provider,
        limit=pagination.limit,
        offset=pagination.offset,
    )
