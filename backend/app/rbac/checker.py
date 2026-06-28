from __future__ import annotations

from uuid import UUID

import asyncpg

from app.rbac.catalog import (
    ACTION_DEFAULT_SCOPE,
    ORG_SCOPED_ACTIONS,
    ActionKey,
    RoleKey,
    ScopeKey,
)
from app.rbac.models import PermissionDecision
from app.rbac.repositories import PermissionCache, RbacRepository, is_allowed
from app.repositories.users import UserRow


class PermissionDeniedError(Exception):
    def __init__(self, decision: PermissionDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Permission denied: {decision.action} on {decision.scope}"
            + (f" (team={decision.team_id})" if decision.team_id else "")
        )


class PermissionChecker:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn
        self._repo = RbacRepository(conn)

    async def can(
        self,
        user: UserRow,
        action: ActionKey,
        *,
        team_id: UUID | None = None,
        scope: ScopeKey | None = None,
    ) -> PermissionDecision:
        resolved_scope = scope or ACTION_DEFAULT_SCOPE[action]
        action_key = action.value
        scope_key = resolved_scope.value

        org_roles = await self._resolve_org_roles(user)
        matrix = await PermissionCache.get_matrix(self._repo)

        if action in ORG_SCOPED_ACTIONS or resolved_scope in {
            ScopeKey.ORGANIZATION,
            ScopeKey.USER,
            ScopeKey.SETTINGS,
        }:
            for role_key in org_roles:
                if is_allowed(
                    matrix, role_key=role_key, action=action, scope=resolved_scope
                ):
                    return PermissionDecision(
                        allowed=True,
                        action=action_key,
                        scope=scope_key,
                        role_key=role_key,
                    )
            return PermissionDecision(
                allowed=False,
                action=action_key,
                scope=scope_key,
            )

        if team_id is None:
            return PermissionDecision(
                allowed=False,
                action=action_key,
                scope=scope_key,
            )

        for role_key in org_roles:
            if role_key == RoleKey.ORG_ADMIN.value and is_allowed(
                matrix,
                role_key=role_key,
                action=action,
                scope=resolved_scope,
            ):
                return PermissionDecision(
                    allowed=True,
                    action=action_key,
                    scope=scope_key,
                    role_key=role_key,
                    team_id=team_id,
                )

        team_role = await self._repo.get_team_role_for_user(user.id, team_id)
        if team_role and is_allowed(
            matrix, role_key=team_role, action=action, scope=resolved_scope
        ):
            return PermissionDecision(
                allowed=True,
                action=action_key,
                scope=scope_key,
                role_key=team_role,
                team_id=team_id,
            )

        return PermissionDecision(
            allowed=False,
            action=action_key,
            scope=scope_key,
            team_id=team_id,
        )

    async def require(
        self,
        user: UserRow,
        action: ActionKey,
        *,
        team_id: UUID | None = None,
        scope: ScopeKey | None = None,
    ) -> PermissionDecision:
        decision = await self.can(user, action, team_id=team_id, scope=scope)
        if not decision.allowed:
            raise PermissionDeniedError(decision)
        return decision

    async def _resolve_org_roles(self, user: UserRow) -> list[str]:
        rows = await self._repo.get_organization_roles_for_user(user.id)
        if rows:
            return [row.role_key for row in rows]
        if user.is_org_admin or user.is_superuser:
            return [RoleKey.ORG_ADMIN.value]
        return [RoleKey.ORG_MEMBER.value]
