from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COGITO_REVIEW_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    review_id: str = ""
    repo_full_name: str = ""
    pr_number: int = 0
    head_sha: str = ""
    git_provider: str = "github"
    github_token: str = ""
    ado_organization: str = ""
    ado_project: str = ""
    ado_pat: str = ""
    gitlab_base_url: str = ""
    gitlab_token: str = ""
    bitbucket_token: str = ""
    bitbucket_dc_base_url: str = ""
    bitbucket_dc_token: str = ""
    llm_provider_id: str = ""
    llm_base_url: str = ""
    llm_api_token: str = ""
    llm_model: str = ""
    opencode_model: str = ""
    callback_url: str = ""
    callback_secret: str = ""
    callback_metadata: str = "{}"
    opencode_agent: str = "code-reviewer"
    system_prompt: str = ""
    opencode_log_level: str = "INFO"
    review_timeout_seconds: int = 600
    workspace_root: str = "/workspaces"

    @property
    def resolved_opencode_model(self) -> str:
        if self.opencode_model.strip():
            return self.opencode_model.strip()
        if self.llm_provider_id and self.llm_model:
            return f"{self.llm_provider_id}/{self.llm_model}"
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()


def clear_agent_settings_cache() -> None:
    get_agent_settings.cache_clear()
