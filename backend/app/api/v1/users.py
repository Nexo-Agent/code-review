import asyncpg
from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_org_admin_user
from app.dependencies import get_conn
from app.repositories.users import UserRow
from app.schemas.user import UserListResponse
from app.services.users import list_users_paginated

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    q: str | None = Query(None, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
    _user: UserRow = Depends(require_org_admin_user),
) -> UserListResponse:
    return await list_users_paginated(conn, search=q, limit=limit, offset=offset)
