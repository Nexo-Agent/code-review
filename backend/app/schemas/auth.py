from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    is_org_admin: bool
    created_at: datetime


class MeResponse(BaseModel):
    user: UserResponse
    team_ids: list[UUID]
    auth_enabled: bool
