from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse


class RepoIntegrationResponse(BaseModel):
    id: UUID
    team_id: UUID
    name: str
    git_provider: str
    repo_full_name: str
    llm_provider_id: UUID | None
    llm_provider_name: str | None
    system_prompt: str
    enabled: bool
    github_webhook_secret_configured: bool
    github_token_configured: bool
    ado_organization: str
    ado_project: str
    ado_pat_configured: bool
    ado_webhook_configured: bool
    gitlab_base_url: str
    gitlab_token_configured: bool
    gitlab_webhook_secret_configured: bool
    webhook_url: str
    created_at: datetime
    updated_at: datetime


class RepoIntegrationCreate(BaseModel):
    name: str = Field(default="", max_length=128)
    git_provider: str = Field(default="github", min_length=1, max_length=32)
    repo_full_name: str = Field(
        default="",
        description="owner/repo or org/project/repo — empty accepts all repositories",
    )
    github_webhook_secret: str = Field(default="", max_length=512)
    github_token: str = Field(default="", max_length=512)
    ado_organization: str = Field(default="", max_length=128)
    ado_project: str = Field(default="", max_length=128)
    ado_pat: str = Field(default="", max_length=512)
    ado_webhook_username: str = Field(default="", max_length=128)
    ado_webhook_password: str = Field(default="", max_length=512)
    gitlab_base_url: str = Field(
        default="",
        max_length=512,
        description="GitLab instance URL; empty uses https://gitlab.com",
    )
    gitlab_token: str = Field(default="", max_length=512)
    gitlab_webhook_secret: str = Field(default="", max_length=512)
    system_prompt: str = Field(
        default="",
        max_length=16384,
        description="Custom OpenCode agent system prompt; empty uses the default",
    )
    llm_provider_id: UUID | None = None
    enabled: bool = True


class RepoIntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    git_provider: str | None = Field(default=None, min_length=1, max_length=32)
    repo_full_name: str | None = Field(
        default=None,
        description="owner/repo or org/project/repo — empty accepts all repositories",
    )
    github_webhook_secret: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    github_token: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    ado_organization: str | None = Field(default=None, max_length=128)
    ado_project: str | None = Field(default=None, max_length=128)
    ado_pat: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    ado_webhook_username: str | None = Field(default=None, max_length=128)
    ado_webhook_password: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    gitlab_base_url: str | None = Field(default=None, max_length=512)
    gitlab_token: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    gitlab_webhook_secret: str | None = Field(
        default=None,
        description="Omit to keep; empty string clears",
    )
    system_prompt: str | None = Field(
        default=None,
        max_length=16384,
        description=(
            "Custom OpenCode agent system prompt; empty string resets to default"
        ),
    )
    enabled: bool | None = None
    llm_provider_id: UUID | None = None
    clear_llm_provider_id: bool = False


class OrgRepositoryResponse(RepoIntegrationResponse):
    team_name: str


class RepoIntegrationListResponse(PaginatedResponse[RepoIntegrationResponse]):
    pass


class OrgRepositoryListResponse(PaginatedResponse[OrgRepositoryResponse]):
    pass
