from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RbacRoleRow:
    id: UUID
    key: str
    display_name: str
    scope_kind: str
    description: str
    is_system: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RbacActionRow:
    id: UUID
    key: str
    display_name: str
    description: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RbacScopeRow:
    id: UUID
    key: str
    display_name: str
    description: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RbacRolePermissionRow:
    id: UUID
    role_id: UUID
    role_key: str
    action_id: UUID
    action_key: str
    resource_scope_id: UUID
    scope_key: str
    allowed: bool


@dataclass(frozen=True, slots=True)
class OrganizationUserRoleRow:
    organization_id: UUID
    user_id: UUID
    role_id: UUID
    role_key: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TeamRoleAssignment:
    team_id: UUID
    role_key: str


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    action: str
    scope: str
    role_key: str | None = None
    team_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class EffectivePermissions:
    organization_roles: list[str]
    organization_actions: list[str]
    team_memberships: list[TeamRoleAssignment]
    team_actions: dict[str, list[str]]
