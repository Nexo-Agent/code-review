import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TeamResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    repo_count: int = 0
    member_count: int = 0
    created_at: datetime


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized):
            msg = "slug must be lowercase alphanumeric with optional hyphens"
            raise ValueError(msg)
        return normalized


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)


class TeamMemberResponse(BaseModel):
    team_id: UUID
    user_id: UUID
    role: str
    user_email: str
    user_name: str
    created_at: datetime


class TeamMemberCreate(BaseModel):
    user_id: UUID
    role: str = Field(default="member", pattern="^(member|viewer|team_admin)$")
