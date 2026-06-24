import asyncpg
from fastapi import APIRouter, Depends

from app.config import get_settings
from app.dependencies import get_conn
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(conn: asyncpg.Connection = Depends(get_conn)) -> HealthResponse:
    settings = get_settings()
    db_status = "ok"
    try:
        await conn.fetchval("SELECT 1")
    except asyncpg.PostgresError:
        db_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
        version=settings.app_version,
    )
