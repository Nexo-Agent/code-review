from __future__ import annotations

from uuid import UUID

import asyncpg

from app.rbac.catalog import ACTION_DEFAULT_SCOPE, ActionKey, RoleKey, ScopeKey
from app.rbac.models import EffectivePermissions
from app.rbac.repositories import PermissionCache, RbacRepository, is_allowed
from app.repositories.teams import TeamRepository
from app.repositories.users import UserRow


async def compute_effective_permissions(
    conn: asyncpg.Connection,
    user: UserRow,
) -> EffectivePermissions:
    repo = RbacRepository(conn)
    matrix = await PermissionCache.get_matrix(repo)

    org_role_rows = await repo.get_organization_roles_for_user(user.id)
    if org_role_rows:
        org_roles = [row.role_key for row in org_role_rows]
    elif user.is_org_admin or user.is_superuser:
        org_roles = [RoleKey.ORG_ADMIN.value]
    else:
        org_roles = [RoleKey.ORG_MEMBER.value]

    org_actions: set[str] = set()
    for role_key in org_roles:
        for action in ActionKey:
            scope = ACTION_DEFAULT_SCOPE[action]
            if scope in {ScopeKey.ORGANIZATION, ScopeKey.USER, ScopeKey.SETTINGS}:
                if is_allowed(matrix, role_key=role_key, action=action, scope=scope):
                    org_actions.add(action.value)

    team_memberships = await repo.list_team_roles_for_user(user.id)
    team_actions: dict[str, list[str]] = {}

    if RoleKey.ORG_ADMIN.value in org_roles:
        teams = await TeamRepository(conn).list_all()
        team_ids = [team.id for team in teams]
    else:
        team_ids = [m.team_id for m in team_memberships]

    membership_by_team = {m.team_id: m.role_key for m in team_memberships}

    for tid in team_ids:
        granted: set[str] = set()
        if RoleKey.ORG_ADMIN.value in org_roles:
            for action in ActionKey:
                scope = ACTION_DEFAULT_SCOPE[action]
                if scope == ScopeKey.TEAM and is_allowed(
                    matrix,
                    role_key=RoleKey.ORG_ADMIN.value,
                    action=action,
                    scope=scope,
                ):
                    granted.add(action.value)
        team_role = membership_by_team.get(tid)
        if team_role:
            for action in ActionKey:
                scope = ACTION_DEFAULT_SCOPE[action]
                if scope == ScopeKey.TEAM and is_allowed(
                    matrix, role_key=team_role, action=action, scope=scope
                ):
                    granted.add(action.value)
        if granted:
            team_actions[str(tid)] = sorted(granted)

    return EffectivePermissions(
        organization_roles=org_roles,
        organization_actions=sorted(org_actions),
        team_memberships=team_memberships,
        team_actions=team_actions,
    )


async def get_accessible_team_ids_from_permissions(
    conn: asyncpg.Connection,
    user: UserRow,
) -> list[UUID]:
    permissions = await compute_effective_permissions(conn, user)
    return [UUID(team_id) for team_id in permissions.team_actions]
