from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_team_member
from app.dependencies import get_conn
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.projects import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def get_projects(
    team_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    _user=Depends(require_team_member),
) -> list[ProjectResponse]:
    try:
        return await list_projects(conn, team_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def post_project(
    team_id: UUID,
    payload: ProjectCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    _user=Depends(require_team_member),
) -> ProjectResponse:
    try:
        return await create_project(conn, team_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_route(
    team_id: UUID,
    project_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    _user=Depends(require_team_member),
) -> ProjectResponse:
    try:
        project = await get_project(conn, project_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if project.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def put_project(
    team_id: UUID,
    project_id: UUID,
    payload: ProjectUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    _user=Depends(require_team_member),
) -> ProjectResponse:
    try:
        project = await get_project(conn, project_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if project.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        return await update_project(conn, project_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_route(
    team_id: UUID,
    project_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    _user=Depends(require_team_member),
) -> None:
    try:
        project = await get_project(conn, project_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if project.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await delete_project(conn, project_id)
