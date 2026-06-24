import asyncpg
from fastapi import APIRouter, Depends

from app.dependencies import get_conn
from app.schemas.integration_settings import (
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
)
from app.services.integration_settings import (
    get_integration_settings,
    to_response,
    update_integration_settings,
)

router = APIRouter()


@router.get("/integration", response_model=IntegrationSettingsResponse)
async def get_settings(
    conn: asyncpg.Connection = Depends(get_conn),
) -> IntegrationSettingsResponse:
    row = await get_integration_settings(conn)
    return to_response(row)


@router.put("/integration", response_model=IntegrationSettingsResponse)
async def put_settings(
    payload: IntegrationSettingsUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> IntegrationSettingsResponse:
    row = await update_integration_settings(conn, payload)
    return to_response(row)
