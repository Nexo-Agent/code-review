import asyncpg
from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard import get_dashboard_summary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary_endpoint(
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> DashboardSummaryResponse:
    return await get_dashboard_summary(conn, auth)
