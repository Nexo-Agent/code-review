from datetime import datetime

from pydantic import BaseModel, Field


class IntegrationSettingsResponse(BaseModel):
    git_provider: str
    github_repo_full_name: str
    github_webhook_secret_configured: bool
    github_token_configured: bool
    llm_provider_id: str
    llm_base_url: str
    llm_model: str
    llm_api_token_configured: bool
    opencode_model: str
    resolved_opencode_model: str
    updated_at: datetime


class IntegrationSettingsUpdate(BaseModel):
    git_provider: str | None = Field(default=None, min_length=1, max_length=32)
    github_repo_full_name: str | None = Field(
        default=None,
        description="owner/repo — empty accepts all repos",
    )
    github_webhook_secret: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    github_token: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    llm_provider_id: str | None = Field(default=None, min_length=1, max_length=64)
    llm_base_url: str | None = Field(default=None, min_length=1, max_length=512)
    llm_api_token: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    llm_model: str | None = Field(default=None, min_length=1, max_length=128)
    opencode_model: str | None = Field(
        default=None,
        description="Optional override for OpenCode model ref",
    )
