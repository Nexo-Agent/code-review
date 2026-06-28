from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import asyncpg

from app.rbac.catalog import ActionKey, RoleKey, ScopeKey
from app.rbac.models import (
    OrganizationUserRoleRow,
    RbacActionRow,
    RbacRolePermissionRow,
    RbacRoleRow,
    RbacScopeRow,
    TeamRoleAssignment,
)
from app.repositories.organizations import DEFAULT_ORG_ID


@dataclass(frozen=True, slots=True)
class PermissionMatrixUpdate:
    role_key: str
    action_key: str
    scope_key: str
    allowed: bool


class RbacRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def list_roles(self) -> list[RbacRoleRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, key, display_name, scope_kind, description, is_system, created_at
            FROM rbac_roles
            ORDER BY scope_kind, key
            """
        )
        return [_role_row(row) for row in rows]

    async def list_actions(self) -> list[RbacActionRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, key, display_name, description, created_at
            FROM rbac_actions
            ORDER BY key
            """
        )
        return [_action_row(row) for row in rows]

    async def list_scopes(self) -> list[RbacScopeRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, key, display_name, description, created_at
            FROM rbac_resource_scopes
            ORDER BY key
            """
        )
        return [_scope_row(row) for row in rows]

    async def list_role_permissions(self) -> list[RbacRolePermissionRow]:
        rows = await self._conn.fetch(
            """
            SELECT rp.id, rp.role_id, r.key AS role_key,
                   rp.action_id, a.key AS action_key,
                   rp.resource_scope_id, s.key AS scope_key,
                   rp.allowed
            FROM rbac_role_permissions rp
            JOIN rbac_roles r ON r.id = rp.role_id
            JOIN rbac_actions a ON a.id = rp.action_id
            JOIN rbac_resource_scopes s ON s.id = rp.resource_scope_id
            ORDER BY s.key, a.key, r.key
            """
        )
        return [_permission_row(row) for row in rows]

    async def get_allowed_permissions(self) -> dict[tuple[str, str, str], bool]:
        rows = await self.list_role_permissions()
        return {
            (row.role_key, row.action_key, row.scope_key): row.allowed for row in rows
        }

    async def update_role_permissions(
        self,
        updates: list[PermissionMatrixUpdate],
    ) -> None:
        for update in updates:
            await self._conn.execute(
                """
                INSERT INTO rbac_role_permissions (
                    role_id, action_id, resource_scope_id, allowed, updated_at
                )
                SELECT r.id, a.id, s.id, $4, now()
                FROM rbac_roles r, rbac_actions a, rbac_resource_scopes s
                WHERE r.key = $1 AND a.key = $2 AND s.key = $3
                ON CONFLICT (role_id, action_id, resource_scope_id)
                DO UPDATE SET allowed = EXCLUDED.allowed, updated_at = now()
                """,
                update.role_key,
                update.action_key,
                update.scope_key,
                update.allowed,
            )

    async def get_organization_roles_for_user(
        self,
        user_id: UUID,
        *,
        organization_id: UUID = DEFAULT_ORG_ID,
    ) -> list[OrganizationUserRoleRow]:
        rows = await self._conn.fetch(
            """
            SELECT our.organization_id, our.user_id, our.role_id,
                   r.key AS role_key, our.created_at
            FROM organization_user_roles our
            JOIN rbac_roles r ON r.id = our.role_id
            WHERE our.user_id = $1 AND our.organization_id = $2
            """,
            user_id,
            organization_id,
        )
        return [_org_role_row(row) for row in rows]

    async def get_team_role_for_user(
        self,
        user_id: UUID,
        team_id: UUID,
    ) -> str | None:
        return await self._conn.fetchval(
            """
            SELECT r.key
            FROM team_members tm
            JOIN rbac_roles r ON r.id = tm.role_id
            WHERE tm.user_id = $1 AND tm.team_id = $2
            """,
            user_id,
            team_id,
        )

    async def list_team_roles_for_user(
        self,
        user_id: UUID,
    ) -> list[TeamRoleAssignment]:
        rows = await self._conn.fetch(
            """
            SELECT tm.team_id, r.key AS role_key
            FROM team_members tm
            JOIN rbac_roles r ON r.id = tm.role_id
            WHERE tm.user_id = $1
            ORDER BY tm.team_id
            """,
            user_id,
        )
        return [
            TeamRoleAssignment(team_id=row["team_id"], role_key=row["role_key"])
            for row in rows
        ]

    async def set_organization_role(
        self,
        user_id: UUID,
        role_key: RoleKey,
        *,
        organization_id: UUID = DEFAULT_ORG_ID,
    ) -> None:
        role_id = await self._conn.fetchval(
            "SELECT id FROM rbac_roles WHERE key = $1",
            role_key.value,
        )
        if role_id is None:
            msg = f"unknown role: {role_key}"
            raise ValueError(msg)

        await self._conn.execute(
            """
            DELETE FROM organization_user_roles
            WHERE organization_id = $1 AND user_id = $2
            """,
            organization_id,
            user_id,
        )
        await self._conn.execute(
            """
            INSERT INTO organization_user_roles (organization_id, user_id, role_id)
            VALUES ($1, $2, $3)
            """,
            organization_id,
            user_id,
            role_id,
        )

        is_org_admin = role_key == RoleKey.ORG_ADMIN
        await self._conn.execute(
            "UPDATE users SET is_org_admin = $2 WHERE id = $1",
            user_id,
            is_org_admin,
        )

    async def get_role_id(self, role_key: RoleKey | str) -> UUID:
        key = role_key.value if isinstance(role_key, RoleKey) else role_key
        role_id = await self._conn.fetchval(
            "SELECT id FROM rbac_roles WHERE key = $1",
            key,
        )
        if role_id is None:
            msg = f"unknown role: {key}"
            raise ValueError(msg)
        return role_id


def _role_row(row: asyncpg.Record) -> RbacRoleRow:
    return RbacRoleRow(
        id=row["id"],
        key=row["key"],
        display_name=row["display_name"],
        scope_kind=row["scope_kind"],
        description=row["description"],
        is_system=row["is_system"],
        created_at=row["created_at"],
    )


def _action_row(row: asyncpg.Record) -> RbacActionRow:
    return RbacActionRow(
        id=row["id"],
        key=row["key"],
        display_name=row["display_name"],
        description=row["description"],
        created_at=row["created_at"],
    )


def _scope_row(row: asyncpg.Record) -> RbacScopeRow:
    return RbacScopeRow(
        id=row["id"],
        key=row["key"],
        display_name=row["display_name"],
        description=row["description"],
        created_at=row["created_at"],
    )


def _permission_row(row: asyncpg.Record) -> RbacRolePermissionRow:
    return RbacRolePermissionRow(
        id=row["id"],
        role_id=row["role_id"],
        role_key=row["role_key"],
        action_id=row["action_id"],
        action_key=row["action_key"],
        resource_scope_id=row["resource_scope_id"],
        scope_key=row["scope_key"],
        allowed=row["allowed"],
    )


def _org_role_row(row: asyncpg.Record) -> OrganizationUserRoleRow:
    return OrganizationUserRoleRow(
        organization_id=row["organization_id"],
        user_id=row["user_id"],
        role_id=row["role_id"],
        role_key=row["role_key"],
        created_at=row["created_at"],
    )


class PermissionCache:
    _matrix: dict[tuple[str, str, str], bool] | None = None
    _loaded_at: datetime | None = None

    @classmethod
    def invalidate(cls) -> None:
        cls._matrix = None
        cls._loaded_at = None

    @classmethod
    async def get_matrix(cls, repo: RbacRepository) -> dict[tuple[str, str, str], bool]:
        if cls._matrix is None:
            cls._matrix = await repo.get_allowed_permissions()
            cls._loaded_at = datetime.now(tz=UTC)
        return cls._matrix

    @classmethod
    async def refresh(cls, repo: RbacRepository) -> None:
        cls.invalidate()
        await cls.get_matrix(repo)


def is_allowed(
    matrix: dict[tuple[str, str, str], bool],
    *,
    role_key: str,
    action: ActionKey | str,
    scope: ScopeKey | str,
) -> bool:
    action_key = action.value if isinstance(action, ActionKey) else action
    scope_key = scope.value if isinstance(scope, ScopeKey) else scope
    return matrix.get((role_key, action_key, scope_key), False)
