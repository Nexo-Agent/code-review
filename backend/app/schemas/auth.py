from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    is_org_admin: bool
    created_at: datetime


class TeamMembershipResponse(BaseModel):
    team_id: UUID
    role_key: str


class PermissionsSummaryResponse(BaseModel):
    organization: list[str]
    teams: dict[str, list[str]]


class MeResponse(BaseModel):
    user: UserResponse
    team_ids: list[UUID]
    auth_enabled: bool
    organization_roles: list[str] = Field(default_factory=list)
    team_memberships: list[TeamMembershipResponse] = Field(default_factory=list)
    permissions: PermissionsSummaryResponse | None = None
