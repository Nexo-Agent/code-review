from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse


class LlmProviderResponse(BaseModel):
    id: UUID
    name: str
    provider_id: str
    base_url: str
    model: str
    opencode_model: str
    resolved_opencode_model: str
    is_default: bool
    enabled: bool
    api_token_configured: bool
    created_at: datetime
    updated_at: datetime


class LlmProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider_id: str = Field(min_length=1, max_length=64)
    base_url: str = Field(min_length=1, max_length=512)
    api_token: str = Field(default="", max_length=512)
    model: str = Field(min_length=1, max_length=128)
    opencode_model: str = Field(default="", max_length=128)
    is_default: bool = False
    enabled: bool = True


class LlmProviderListResponse(PaginatedResponse[LlmProviderResponse]):
    pass


class LlmProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    provider_id: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: str | None = Field(default=None, min_length=1, max_length=512)
    api_token: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    model: str | None = Field(default=None, min_length=1, max_length=128)
    opencode_model: str | None = Field(default=None, max_length=128)
    is_default: bool | None = None
    enabled: bool | None = None
