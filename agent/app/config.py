from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://app:app@localhost:5432/app?sslmode=disable"
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXO_COREVIEW_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    git_provider: str = "github"
    github_token: str = ""
    mcp_server_url: str = "http://127.0.0.1:8001/sse"
    mcp_server_port: int = 8001
    mcp_bind_host: str = "127.0.0.1"
    opencode_server_url: str = "http://localhost:4096"
    opencode_server_password: str = ""
    opencode_server_username: str = "opencode"
    opencode_bind_host: str = "0.0.0.0"
    opencode_port: int = 4096
    opencode_agent: str = "code-reviewer"
    review_timeout_seconds: int = 600
    workspace_root: str = "/workspaces"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
