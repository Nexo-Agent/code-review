import json
import logging
import os
from pathlib import Path

from app.config import CodeReviewSettings, get_code_review_settings
from app.repositories.integration_settings import (
    IntegrationSettingsRepository,
    IntegrationSettingsRow,
)
from app.schemas.integration_settings import (
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENCODE_CONFIG_PATH = Path(
    os.environ.get("NEXO_COREVIEW_OPENCODE_CONFIG_PATH", "opencode.generated.json")
)


def to_response(row: IntegrationSettingsRow) -> IntegrationSettingsResponse:
    return IntegrationSettingsResponse(
        git_provider=row.git_provider,
        github_repo_full_name=row.github_repo_full_name,
        github_webhook_secret_configured=bool(row.github_webhook_secret),
        github_token_configured=bool(row.github_token),
        llm_provider_id=row.llm_provider_id,
        llm_base_url=row.llm_base_url,
        llm_model=row.llm_model,
        llm_api_token_configured=bool(row.llm_api_token),
        opencode_model=row.opencode_model,
        resolved_opencode_model=row.resolved_opencode_model,
        updated_at=row.updated_at,
    )


async def get_integration_settings(conn) -> IntegrationSettingsRow:
    repo = IntegrationSettingsRepository(conn)
    row = await repo.get()
    return await _seed_from_env_if_empty(conn, row)


async def update_integration_settings(
    conn,
    payload: IntegrationSettingsUpdate,
) -> IntegrationSettingsRow:
    repo = IntegrationSettingsRepository(conn)
    data = payload.model_dump(exclude_unset=True)

    clear_webhook_secret = (
        "github_webhook_secret" in data and data["github_webhook_secret"] == ""
    )
    clear_github_token = "github_token" in data and data["github_token"] == ""
    clear_llm_api_token = "llm_api_token" in data and data["llm_api_token"] == ""

    row = await repo.update(
        git_provider=data.get("git_provider"),
        github_repo_full_name=data.get("github_repo_full_name"),
        github_webhook_secret=data.get("github_webhook_secret"),
        github_token=data.get("github_token"),
        llm_provider_id=data.get("llm_provider_id"),
        llm_base_url=data.get("llm_base_url"),
        llm_api_token=data.get("llm_api_token"),
        llm_model=data.get("llm_model"),
        opencode_model=data.get("opencode_model"),
        clear_webhook_secret=clear_webhook_secret,
        clear_github_token=clear_github_token,
        clear_llm_api_token=clear_llm_api_token,
    )
    sync_opencode_config(row)
    logger.info("Integration settings updated at %s", row.updated_at)
    return row


async def _seed_from_env_if_empty(
    conn,
    row: IntegrationSettingsRow,
) -> IntegrationSettingsRow:
    env = get_code_review_settings()
    if _row_has_user_config(row):
        return row

    if not any(
        [
            env.github_webhook_secret,
            env.github_token,
            env.llm_api_token,
            env.llm_base_url != "https://api.openai.com/v1",
        ]
    ):
        return row

    repo = IntegrationSettingsRepository(conn)
    logger.info("Seeding integration settings from environment (one-time bootstrap)")
    return await repo.update(
        github_webhook_secret=env.github_webhook_secret or None,
        github_token=env.github_token or None,
        llm_provider_id=env.llm_provider_id,
        llm_base_url=env.llm_base_url,
        llm_api_token=env.llm_api_token or None,
        llm_model=env.llm_model,
        opencode_model=env.opencode_model or None,
    )


def _row_has_user_config(row: IntegrationSettingsRow) -> bool:
    return bool(
        row.github_webhook_secret
        or row.github_token
        or row.llm_api_token
        or row.github_repo_full_name
    )


def sync_opencode_config(
    row: IntegrationSettingsRow,
    output_path: Path | None = None,
) -> Path:
    config = build_opencode_config_from_integration(row)
    path = output_path or DEFAULT_OPENCODE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def build_opencode_config_from_integration(
    integration: IntegrationSettingsRow,
    infra: CodeReviewSettings | None = None,
) -> dict:
    infra = infra or get_code_review_settings()
    provider_id = integration.llm_provider_id
    model_id = integration.llm_model
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            provider_id: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "OpenAI Compatible API",
                "options": {
                    "baseURL": integration.llm_base_url,
                    "apiKey": integration.llm_api_token,
                },
                "models": {
                    model_id: {
                        "name": model_id,
                    }
                },
            }
        },
        "agent": {
            infra.opencode_agent: {
                "description": "Reviews PR for bugs, security, and maintainability",
                "mode": "subagent",
                "model": integration.resolved_opencode_model,
                "prompt": (
                    "You are a code reviewer. Analyze the pull request diff and "
                    "return findings as JSON matching the outputFormat schema. "
                    "Focus on bugs, security issues, performance problems, and "
                    "missing tests."
                ),
                "permission": {
                    "edit": "deny",
                    "write": "deny",
                    "bash": {"git *": "allow", "*": "deny"},
                },
            }
        },
    }


def build_providers_config(
    integration: IntegrationSettingsRow,
    infra: CodeReviewSettings | None = None,
) -> CodeReviewSettings:
    infra = infra or get_code_review_settings()
    return CodeReviewSettings(
        git_provider=integration.git_provider,
        github_webhook_secret=integration.github_webhook_secret,
        github_token=integration.github_token,
        celery_broker_url=infra.celery_broker_url,
        runtime_provider=infra.runtime_provider,
        workspace_root=infra.workspace_root,
        workspace_image=infra.workspace_image,
        llm_provider_id=integration.llm_provider_id,
        llm_base_url=integration.llm_base_url,
        llm_api_token=integration.llm_api_token,
        llm_model=integration.llm_model,
        opencode_agent=infra.opencode_agent,
        opencode_model=integration.opencode_model,
        opencode_server_url=infra.opencode_server_url,
        opencode_server_password=infra.opencode_server_password,
        opencode_server_username=infra.opencode_server_username,
        review_timeout_seconds=infra.review_timeout_seconds,
    )
