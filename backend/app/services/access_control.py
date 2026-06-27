from uuid import UUID

from app.repositories.organizations import DEFAULT_ORG_ID, OrganizationRepository
from app.repositories.team_members import TeamMemberRepository
from app.repositories.teams import TeamRepository
from app.repositories.users import UserRow


class AccessDeniedError(Exception):
    pass


async def get_accessible_team_ids(
    conn,
    user: UserRow,
) -> list[UUID]:
    if user.is_org_admin:
        teams = await TeamRepository(conn).list_all()
        return [team.id for team in teams]
    return await TeamMemberRepository(conn).list_team_ids_for_user(user.id)


async def require_team_access(
    conn,
    user: UserRow,
    team_id: UUID,
) -> None:
    if user.is_org_admin:
        return
    is_member = await TeamMemberRepository(conn).is_member(team_id, user.id)
    if not is_member:
        raise AccessDeniedError


async def require_org_admin(user: UserRow) -> None:
    if not user.is_org_admin:
        raise AccessDeniedError


async def get_default_organization_id(conn) -> UUID:
    org = await OrganizationRepository(conn).get_default()
    return org.id if org else DEFAULT_ORG_ID
