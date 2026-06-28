from uuid import UUID

from app.rbac.catalog import ActionKey, RoleKey
from app.rbac.checker import PermissionChecker, PermissionDeniedError
from app.rbac.effective_permissions import get_accessible_team_ids_from_permissions
from app.repositories.users import UserRow


class AccessDeniedError(Exception):
    pass


async def get_accessible_team_ids(
    conn,
    user: UserRow,
) -> list[UUID]:
    return await get_accessible_team_ids_from_permissions(conn, user)


async def require_team_access(
    conn,
    user: UserRow,
    team_id: UUID,
    *,
    action: ActionKey = ActionKey.TEAM_READ,
) -> None:
    checker = PermissionChecker(conn)
    try:
        await checker.require(user, action, team_id=team_id)
    except PermissionDeniedError as exc:
        raise AccessDeniedError from exc


async def require_org_admin(user: UserRow) -> None:
    if not user.is_org_admin:
        raise AccessDeniedError


async def get_default_organization_id(conn) -> UUID:
    from app.repositories.organizations import DEFAULT_ORG_ID, OrganizationRepository

    org = await OrganizationRepository(conn).get_default()
    return org.id if org else DEFAULT_ORG_ID


async def sync_user_org_role(
    conn,
    user_id: UUID,
    *,
    is_org_admin: bool,
) -> None:
    from app.rbac.repositories import RbacRepository

    repo = RbacRepository(conn)
    role = RoleKey.ORG_ADMIN if is_org_admin else RoleKey.ORG_MEMBER
    await repo.set_organization_role(user_id, role)
