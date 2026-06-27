from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.pagination import PaginatedResponse


class UserListItemResponse(BaseModel):
    id: UUID
    email: str
    name: str
    username: str | None
    auth_source: str
    is_org_admin: bool
    is_superuser: bool
    team_names: str
    created_at: datetime


class UserListResponse(PaginatedResponse[UserListItemResponse]):
    pass
