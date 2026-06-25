from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_conn
from app.schemas.llm_provider import (
    LlmProviderCreate,
    LlmProviderResponse,
    LlmProviderUpdate,
)
from app.services.llm_providers import (
    create_llm_provider,
    delete_llm_provider,
    list_llm_providers,
    update_llm_provider,
)

router = APIRouter()


@router.get("", response_model=list[LlmProviderResponse])
async def get_llm_providers(
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[LlmProviderResponse]:
    return await list_llm_providers(conn)


@router.post(
    "",
    response_model=LlmProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_llm_provider(
    payload: LlmProviderCreate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> LlmProviderResponse:
    return await create_llm_provider(conn, payload)


@router.put("/{provider_id}", response_model=LlmProviderResponse)
async def put_llm_provider(
    provider_id: UUID,
    payload: LlmProviderUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> LlmProviderResponse:
    try:
        return await update_llm_provider(conn, provider_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_llm_provider(
    provider_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> None:
    await delete_llm_provider(conn, provider_id)
