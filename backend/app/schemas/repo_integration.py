from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RepoIntegrationResponse(BaseModel):
    id: UUID
    name: str
    git_provider: str
    repo_full_name: str
    llm_provider_id: UUID | None
    llm_provider_name: str | None
    system_prompt: str
    enabled: bool
    github_webhook_secret_configured: bool
    github_token_configured: bool
    created_at: datetime
    updated_at: datetime


class RepoIntegrationCreate(BaseModel):
    name: str = Field(default="", max_length=128)
    git_provider: str = Field(default="github", min_length=1, max_length=32)
    repo_full_name: str = Field(
        default="",
        description="owner/repo — empty accepts all repositories",
    )
    github_webhook_secret: str = Field(default="", max_length=512)
    github_token: str = Field(default="", max_length=512)
    llm_provider_id: UUID | None = None
    system_prompt: str = Field(
        default="",
        max_length=16384,
        description="Custom OpenCode agent system prompt; empty uses the default",
    )
    enabled: bool = True


class RepoIntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    git_provider: str | None = Field(default=None, min_length=1, max_length=32)
    repo_full_name: str | None = Field(
        default=None,
        description="owner/repo — empty accepts all repositories",
    )
    github_webhook_secret: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    github_token: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    llm_provider_id: UUID | None = None
    clear_llm_provider_id: bool = False
    system_prompt: str | None = Field(
        default=None,
        max_length=16384,
        description=(
            "Custom OpenCode agent system prompt; empty string resets to default"
        ),
    )
    enabled: bool | None = None
