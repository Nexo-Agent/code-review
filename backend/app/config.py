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
    cors_origins: list[str] = ["http://localhost:5173"]
    static_dir: str = "/app/static"
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10


class CodeReviewSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXO_COREVIEW_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    git_provider: str = "github"
    github_webhook_secret: str = ""
    github_token: str = ""
    github_app_id: str = ""
    github_private_key: str = ""
    celery_broker_url: str = "redis://localhost:6379/0"
    runtime_provider: str = "docker"
    workspace_root: str = "/workspaces"
    workspace_image: str = ""
    llm_provider_id: str = "openai-compat"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_token: str = ""
    llm_model: str = "gpt-4o"
    opencode_agent: str = "code-reviewer"
    opencode_model: str = ""
    opencode_server_url: str = "http://localhost:4096"
    opencode_server_password: str = ""
    opencode_server_username: str = "opencode"
    review_timeout_seconds: int = 600

    @property
    def resolved_opencode_model(self) -> str:
        if self.opencode_model:
            return self.opencode_model
        return f"{self.llm_provider_id}/{self.llm_model}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_code_review_settings() -> CodeReviewSettings:
    return CodeReviewSettings()
