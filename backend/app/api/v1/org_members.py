import asyncpg
from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.schemas.team import OrgMemberResponse
from app.services.teams import list_org_members

router = APIRouter()


@router.get("", response_model=list[OrgMemberResponse])
async def get_org_members(
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> list[OrgMemberResponse]:
    return await list_org_members(conn, auth.accessible_team_ids)
