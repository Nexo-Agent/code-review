from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ReviewRuntimeConfig:
    """Per-repo review credentials loaded from Postgres, not from env."""

    git_provider: str
    github_webhook_secret: str
    github_token: str
    llm_provider_id: str
    llm_base_url: str
    llm_api_token: str
    llm_model: str
    opencode_model: str = ""

    @property
    def resolved_opencode_model(self) -> str:
        if self.opencode_model.strip():
            return self.opencode_model.strip()
        return f"{self.llm_provider_id}/{self.llm_model}"


class CodeReviewSettings(BaseSettings):
    """Infrastructure settings from NEXO_COREVIEW_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="NEXO_COREVIEW_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    celery_broker_url: str = "redis://localhost:6379/0"
    runtime_provider: str = "docker"
    workspace_root: str = "/workspaces"
    workspace_image: str = ""
    # Empty = auto-detect socket (macOS/Linux/Windows). See docker/client.py.
    docker_host: str = ""
    # Minimal git image for DockerCommandRunner; ENTRYPOINT is "git".
    git_image: str = "alpine/git:latest"
    mcp_server_url: str = "http://mcp-serve:8001/sse"
    mcp_server_port: int = 8001
    opencode_agent: str = "code-reviewer"
    opencode_log_level: str = "INFO"
    review_timeout_seconds: int = 600
    agent_image: str = "nexo-coreview-agent:dev"
    # Docker network for per-review agent containers (e.g. coreview in Compose).
    # Empty = publish OpenCode port to host (native worker dev).
    agent_network: str = ""
    # K8s runtime (stub — not implemented yet)
    k8s_namespace: str = "coreview"
    k8s_kubeconfig_path: str = ""
    k8s_agent_config_configmap: str = "opencode-config"
    k8s_image_pull_secret: str = ""
    agent_callback_url: str = "http://localhost:8000/api/v1/agent/review-events"
    agent_callback_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_code_review_settings() -> CodeReviewSettings:
    return CodeReviewSettings()
