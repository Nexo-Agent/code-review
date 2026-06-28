from dataclasses import dataclass
from uuid import UUID

import asyncpg
from fastapi import Cookie, Depends, HTTPException, Request, status

from app.auth.session import get_session_user_id
from app.config import get_code_review_settings
from app.dependencies import get_conn
from app.rbac.catalog import ActionKey
from app.rbac.checker import PermissionChecker, PermissionDeniedError
from app.rbac.effective_permissions import compute_effective_permissions
from app.rbac.models import EffectivePermissions
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.users import UserRepository, UserRow
from app.services.access_control import (
    AccessDeniedError,
    get_accessible_team_ids,
    require_org_admin,
)

SESSION_COOKIE = "cogito_session"
DEV_USER_ID = UUID("00000000-0000-4000-8000-000000000099")


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: UserRow
    accessible_team_ids: list[UUID]
    auth_enabled: bool
    permissions: EffectivePermissions | None = None


async def _get_dev_user(conn: asyncpg.Connection) -> UserRow:
    repo = UserRepository(conn)
    user = await repo.get(DEV_USER_ID)
    if user is not None:
        return user
    return await repo.upsert_oidc_user(
        oidc_sub="dev-bypass",
        email="dev@localhost",
        name="Dev Admin",
        is_org_admin=True,
    )


async def get_current_user(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> UserRow:
    settings = get_code_review_settings()

    if session_id:
        user_id = await get_session_user_id(session_id)
        if user_id is not None:
            user = await UserRepository(conn).get(user_id)
            if user is not None:
                return user

    if not settings.auth_enabled:
        from app.services.install import SetupRequiredError, assert_setup_completed

        try:
            await assert_setup_completed(conn)
        except SetupRequiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Setup required",
            )
        return await _get_dev_user(conn)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


async def get_auth_context(
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> AuthContext:
    settings = get_code_review_settings()
    team_ids = await get_accessible_team_ids(conn, user)
    permissions = await compute_effective_permissions(conn, user)
    return AuthContext(
        user=user,
        accessible_team_ids=team_ids,
        auth_enabled=settings.auth_enabled,
        permissions=permissions,
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied",
    )


async def require_permission(
    user: UserRow,
    conn: asyncpg.Connection,
    action: ActionKey,
    *,
    team_id: UUID | None = None,
) -> UserRow:
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action, team_id=team_id)
    except PermissionDeniedError:
        raise _forbidden()
    return user


async def require_org_admin_user(
    user: UserRow = Depends(get_current_user),
) -> UserRow:
    try:
        await require_org_admin(user)
    except AccessDeniedError:
        raise _forbidden()
    return user


async def require_team_member(
    team_id: UUID,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    return await require_permission(user, conn, ActionKey.TEAM_READ, team_id=team_id)


async def require_team_action(
    team_id: UUID,
    action: ActionKey,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    return await require_permission(user, conn, action, team_id=team_id)


async def require_org_action(
    action: ActionKey,
    user: UserRow = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_conn),
) -> UserRow:
    return await require_permission(user, conn, action)


def require_org_action_dep(action: ActionKey):
    async def _dep(
        user: UserRow = Depends(get_current_user),
        conn: asyncpg.Connection = Depends(get_conn),
    ) -> UserRow:
        return await require_permission(user, conn, action)

    return _dep


def require_team_action_dep(action: ActionKey):
    async def _dep(
        team_id: UUID,
        user: UserRow = Depends(get_current_user),
        conn: asyncpg.Connection = Depends(get_conn),
    ) -> UserRow:
        return await require_permission(user, conn, action, team_id=team_id)

    return _dep


async def assert_review_access(
    conn: asyncpg.Connection,
    user: UserRow,
    team_id: UUID,
    *,
    action: ActionKey = ActionKey.REVIEW_READ,
) -> None:
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action, team_id=team_id)
    except PermissionDeniedError:
        raise _forbidden()


__all__ = [
    "AuthContext",
    "DEV_USER_ID",
    "DEFAULT_ORG_ID",
    "SESSION_COOKIE",
    "assert_review_access",
    "get_auth_context",
    "get_current_user",
    "require_org_action",
    "require_org_action_dep",
    "require_org_admin_user",
    "require_permission",
    "require_team_action",
    "require_team_action_dep",
    "require_team_member",
]
