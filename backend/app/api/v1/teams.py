from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user, require_org_admin_user
from app.dependencies import get_conn
from app.schemas.repo_integration import TeamRepositoryResponse
from app.schemas.team import (
    TeamCreate,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)
from app.services.access_control import AccessDeniedError, require_team_access
from app.services.repo_integrations import list_repo_integrations_for_team
from app.services.teams import (
    add_team_member,
    create_team,
    delete_team,
    list_team_members,
    list_teams,
    remove_team_member,
    update_team,
)

router = APIRouter()


@router.get("", response_model=list[TeamResponse])
async def get_teams(
    conn: asyncpg.Connection = Depends(get_conn),
    user=Depends(get_current_user),
) -> list[TeamResponse]:
    return await list_teams(conn, user=user)


@router.get("/{team_id}/repositories", response_model=list[TeamRepositoryResponse])
async def get_team_repositories(
    team_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    user=Depends(get_current_user),
) -> list[TeamRepositoryResponse]:
    try:
        await require_team_access(conn, user, team_id)
    except AccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        return await list_repo_integrations_for_team(conn, team_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def post_team(
    payload: TeamCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_admin_user),
) -> TeamResponse:
    return await create_team(conn, payload)


@router.put("/{team_id}", response_model=TeamResponse)
async def put_team(
    team_id: UUID,
    payload: TeamUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    user=Depends(require_org_admin_user),
) -> TeamResponse:
    try:
        return await update_team(conn, team_id, payload)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_route(
    team_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_admin_user),
) -> None:
    await delete_team(conn, team_id)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def get_team_members(
    team_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    user=Depends(get_current_user),
) -> list[TeamMemberResponse]:
    try:
        await require_team_access(conn, user, team_id)
    except AccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return await list_team_members(conn, team_id)


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_team_member(
    team_id: UUID,
    payload: TeamMemberCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_admin_user),
) -> TeamMemberResponse:
    try:
        return await add_team_member(conn, team_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_member(
    team_id: UUID,
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_admin_user),
) -> None:
    await remove_team_member(conn, team_id, user_id)
