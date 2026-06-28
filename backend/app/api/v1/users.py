from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.pagination import PaginationParams
from app.auth.dependencies import require_org_action_dep
from app.dependencies import get_conn
from app.rbac.catalog import ActionKey, RoleKey
from app.rbac.repositories import RbacRepository
from app.repositories.users import UserRepository, UserRow
from app.schemas.auth import UserResponse
from app.schemas.user import UserListResponse
from app.services.users import list_users_paginated

router = APIRouter()


class OrganizationRoleUpdate(BaseModel):
    role_key: str = Field(pattern="^(org_admin|org_member)$")


@router.get("", response_model=UserListResponse)
async def list_users(
    q: str | None = Query(None, max_length=200),
    pagination: PaginationParams = Depends(),
    conn: asyncpg.Connection = Depends(get_conn),
    _user: UserRow = Depends(require_org_action_dep(ActionKey.USER_READ)),
) -> UserListResponse:
    return await list_users_paginated(
        conn,
        search=q,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.put("/{user_id}/organization-role", response_model=UserResponse)
async def update_organization_role(
    user_id: UUID,
    payload: OrganizationRoleUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    _admin: UserRow = Depends(require_org_action_dep(ActionKey.USER_ASSIGN_ORG_ADMIN)),
) -> UserResponse:
    user = await UserRepository(conn).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if user.is_superuser and payload.role_key != RoleKey.ORG_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote superuser",
        )
    role = RoleKey(payload.role_key)
    rbac = RbacRepository(conn)
    before_roles = await rbac.get_organization_roles_for_user(user_id)
    await rbac.set_organization_role(user_id, role)
    from app.services.audit import log_audit_event

    await log_audit_event(
        conn,
        actor_user_id=_admin.id,
        event_type="organization_role.changed",
        target_type="user",
        target_id=str(user_id),
        before_state={"roles": [r.role_key for r in before_roles]},
        after_state={"role": payload.role_key},
    )
    refreshed = await UserRepository(conn).get(user_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return UserResponse(
        id=refreshed.id,
        email=refreshed.email,
        name=refreshed.name,
        is_org_admin=refreshed.is_org_admin,
        created_at=refreshed.created_at,
    )
