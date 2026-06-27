from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectResponse(BaseModel):
    id: UUID
    team_id: UUID
    name: str
    description: str
    llm_provider_id: UUID | None
    llm_provider_name: str | None
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)
    llm_provider_id: UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    llm_provider_id: UUID | None = None
    clear_llm_provider_id: bool = False
