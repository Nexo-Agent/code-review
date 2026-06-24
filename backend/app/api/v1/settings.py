from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_conn
from app.schemas.integration_settings import (
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
)
from app.schemas.llm_provider import (
    LlmProviderCreate,
    LlmProviderResponse,
    LlmProviderUpdate,
)
from app.schemas.repo_integration import (
    RepoIntegrationCreate,
    RepoIntegrationResponse,
    RepoIntegrationUpdate,
)
from app.services.integration_settings import (
    get_integration_settings,
    to_response,
    update_integration_settings,
)
from app.services.llm_providers import (
    create_llm_provider,
    delete_llm_provider,
    list_llm_providers,
    update_llm_provider,
)
from app.services.repo_integrations import (
    create_repo_integration,
    delete_repo_integration,
    list_repo_integrations,
    update_repo_integration,
)

router = APIRouter()


@router.get("/llm-providers", response_model=list[LlmProviderResponse])
async def get_llm_providers(
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[LlmProviderResponse]:
    return await list_llm_providers(conn)


@router.post(
    "/llm-providers",
    response_model=LlmProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_llm_provider(
    payload: LlmProviderCreate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> LlmProviderResponse:
    return await create_llm_provider(conn, payload)


@router.put("/llm-providers/{provider_id}", response_model=LlmProviderResponse)
async def put_llm_provider(
    provider_id: UUID,
    payload: LlmProviderUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> LlmProviderResponse:
    try:
        return await update_llm_provider(conn, provider_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/llm-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_llm_provider(
    provider_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> None:
    await delete_llm_provider(conn, provider_id)


@router.get("/repos", response_model=list[RepoIntegrationResponse])
async def get_repo_integrations(
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[RepoIntegrationResponse]:
    return await list_repo_integrations(conn)


@router.post(
    "/repos",
    response_model=RepoIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_repo_integration(
    payload: RepoIntegrationCreate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RepoIntegrationResponse:
    return await create_repo_integration(conn, payload)


@router.put("/repos/{integration_id}", response_model=RepoIntegrationResponse)
async def put_repo_integration(
    integration_id: UUID,
    payload: RepoIntegrationUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> RepoIntegrationResponse:
    try:
        return await update_repo_integration(conn, integration_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/repos/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repo_integration(
    integration_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> None:
    await delete_repo_integration(conn, integration_id)


@router.get("/integration", response_model=IntegrationSettingsResponse)
async def get_settings_legacy(
    conn: asyncpg.Connection = Depends(get_conn),
) -> IntegrationSettingsResponse:
    """Deprecated: use /settings/llm-providers and /settings/repos."""
    row = await get_integration_settings(conn)
    return to_response(row)


@router.put("/integration", response_model=IntegrationSettingsResponse)
async def put_settings_legacy(
    payload: IntegrationSettingsUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> IntegrationSettingsResponse:
    """Deprecated: use /settings/llm-providers and /settings/repos."""
    row = await update_integration_settings(conn, payload)
    return to_response(row)
