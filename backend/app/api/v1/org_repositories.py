import asyncpg
from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.schemas.repo_integration import OrgRepositoryResponse
from app.services.repo_integrations import list_repo_integrations_for_teams

router = APIRouter()


@router.get("", response_model=list[OrgRepositoryResponse])
async def get_org_repositories(
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> list[OrgRepositoryResponse]:
    return await list_repo_integrations_for_teams(conn, auth.accessible_team_ids)
