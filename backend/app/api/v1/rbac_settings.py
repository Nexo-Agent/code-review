import asyncpg
from fastapi import APIRouter, Depends

from app.auth.dependencies import require_org_action_dep
from app.dependencies import get_conn
from app.rbac.catalog import ActionKey
from app.rbac.repositories import (
    PermissionCache,
    PermissionMatrixUpdate,
    RbacRepository,
)
from app.repositories.users import UserRow
from app.schemas.rbac import (
    RbacActionResponse,
    RbacCatalogResponse,
    RbacRoleResponse,
    RbacScopeResponse,
    RolePermissionBatchUpdate,
    RolePermissionEntry,
    RolePermissionMatrixResponse,
)

router = APIRouter()


@router.get("/catalog", response_model=RbacCatalogResponse)
async def get_rbac_catalog(
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_RBAC_READ)),
) -> RbacCatalogResponse:
    repo = RbacRepository(conn)
    roles = await repo.list_roles()
    actions = await repo.list_actions()
    scopes = await repo.list_scopes()
    return RbacCatalogResponse(
        roles=[
            RbacRoleResponse(
                key=r.key,
                display_name=r.display_name,
                scope_kind=r.scope_kind,
                description=r.description,
            )
            for r in roles
        ],
        actions=[
            RbacActionResponse(
                key=a.key,
                display_name=a.display_name,
                description=a.description,
            )
            for a in actions
        ],
        scopes=[
            RbacScopeResponse(
                key=s.key,
                display_name=s.display_name,
                description=s.description,
            )
            for s in scopes
        ],
    )


@router.get("/permissions", response_model=RolePermissionMatrixResponse)
async def get_role_permissions(
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_RBAC_READ)),
) -> RolePermissionMatrixResponse:
    repo = RbacRepository(conn)
    rows = await repo.list_role_permissions()
    return RolePermissionMatrixResponse(
        items=[
            RolePermissionEntry(
                role_key=row.role_key,
                action_key=row.action_key,
                scope_key=row.scope_key,
                allowed=row.allowed,
            )
            for row in rows
        ]
    )


@router.put("/permissions", response_model=RolePermissionMatrixResponse)
async def update_role_permissions(
    payload: RolePermissionBatchUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    admin: UserRow = Depends(require_org_action_dep(ActionKey.SETTINGS_RBAC_UPDATE)),
) -> RolePermissionMatrixResponse:
    from app.services.audit import log_audit_event

    repo = RbacRepository(conn)
    before = await repo.list_role_permissions()
    await repo.update_role_permissions(
        [
            PermissionMatrixUpdate(
                role_key=u.role_key,
                action_key=u.action_key,
                scope_key=u.scope_key,
                allowed=u.allowed,
            )
            for u in payload.updates
        ]
    )
    await PermissionCache.refresh(repo)
    after = await repo.list_role_permissions()
    await log_audit_event(
        conn,
        actor_user_id=admin.id,
        event_type="permission_matrix.updated",
        target_type="rbac_role_permissions",
        before_state={"count": len(before)},
        after_state={"updates": len(payload.updates), "count": len(after)},
    )
    rows = after
    return RolePermissionMatrixResponse(
        items=[
            RolePermissionEntry(
                role_key=row.role_key,
                action_key=row.action_key,
                scope_key=row.scope_key,
                allowed=row.allowed,
            )
            for row in rows
        ]
    )
