from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_conn
from app.schemas.repo_integration import (
    RepoIntegrationCreate,
    RepoIntegrationResponse,
    RepoIntegrationUpdate,
)
from app.services.repo_integrations import (
    create_repo_integration,
    delete_repo_integration,
    list_repo_integrations,
    update_repo_integration,
)

router = APIRouter()


@router.get("", response_model=list[RepoIntegrationResponse])
async def get_repo_integrations(
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[RepoIntegrationResponse]:
    return await list_repo_integrations(conn)


@router.post(
    "",
    response_model=RepoIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_repo_integration(
    payload: RepoIntegrationCreate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RepoIntegrationResponse:
    return await create_repo_integration(conn, payload)


@router.put("/{integration_id}", response_model=RepoIntegrationResponse)
async def put_repo_integration(
    integration_id: UUID,
    payload: RepoIntegrationUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RepoIntegrationResponse:
    try:
        return await update_repo_integration(conn, integration_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repo_integration(
    integration_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> None:
    await delete_repo_integration(conn, integration_id)
