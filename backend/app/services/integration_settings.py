import json
import logging
import os
from pathlib import Path
from uuid import UUID

from app.config import CodeReviewSettings, get_code_review_settings
from app.repositories.llm_providers import LlmProviderRepository, LlmProviderRow
from app.repositories.repo_integrations import RepoIntegrationRepository
from app.repositories.integration_settings import (
    IntegrationSettingsRepository,
    IntegrationSettingsRow,
)
from app.schemas.integration_settings import (
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
)
from app.services.provider_resolution import (
    build_providers_config,
    sync_opencode_config_from_db,
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


async def _legacy_row_from_multi(conn) -> IntegrationSettingsRow | None:
    llm_repo = LlmProviderRepository(conn)
    repo_repo = RepoIntegrationRepository(conn)
    default_llm = await llm_repo.get_default()
    repos = await repo_repo.list_all()
    if default_llm is None and not repos:
        return None

    repo = next((r for r in repos if not r.repo_full_name.strip()), None)
    if repo is None and repos:
        repo = repos[0]

    if default_llm is None or repo is None:
        return None

    from datetime import UTC, datetime

    now = max(
        default_llm.updated_at,
        repo.updated_at if repo else default_llm.updated_at,
    )
    return IntegrationSettingsRow(
        git_provider=repo.git_provider if repo else "github",
        github_repo_full_name=repo.repo_full_name if repo else "",
        github_webhook_secret=repo.github_webhook_secret if repo else "",
        github_token=repo.github_token if repo else "",
        llm_provider_id=default_llm.provider_id,
        llm_base_url=default_llm.base_url,
        llm_api_token=default_llm.api_token,
        llm_model=default_llm.model,
        opencode_model=default_llm.opencode_model,
        updated_at=now,
    )


async def get_integration_settings(conn) -> IntegrationSettingsRow:
    legacy = await IntegrationSettingsRepository(conn).get()
    multi = await _legacy_row_from_multi(conn)
    if multi is not None:
        return multi
    row = await _seed_from_env_if_empty(conn, legacy)
    return row


async def update_integration_settings(
    conn,
    payload: IntegrationSettingsUpdate,
) -> IntegrationSettingsRow:
    """Legacy PUT: updates default LLM provider and first/catch-all repo."""
    data = payload.model_dump(exclude_unset=True)
    llm_repo = LlmProviderRepository(conn)
    repo_repo = RepoIntegrationRepository(conn)

    default_llm = await llm_repo.get_default()
    if default_llm is None:
        default_llm = await llm_repo.create(
            name="Default",
            provider_id=data.get("llm_provider_id") or "openai-compat",
            base_url=data.get("llm_base_url") or "https://api.openai.com/v1",
            api_token=data.get("llm_api_token") or "",
            model=data.get("llm_model") or "gpt-4o",
            opencode_model=data.get("opencode_model") or "",
            is_default=True,
        )
    else:
        clear_llm_api_token = (
            "llm_api_token" in data and data["llm_api_token"] == ""
        )
        default_llm = await llm_repo.update(
            default_llm.id,
            provider_id_key=data.get("llm_provider_id"),
            base_url=data.get("llm_base_url"),
            api_token=data.get("llm_api_token"),
            model=data.get("llm_model"),
            opencode_model=data.get("opencode_model"),
            clear_api_token=clear_llm_api_token,
            is_default=True,
        )

    repos = await repo_repo.list_all()
    repo = next((r for r in repos if not r.repo_full_name.strip()), None)
    if repo is None and repos:
        repo = repos[0]

    if repo is None:
        repo = await repo_repo.create(
            name="All repositories",
            git_provider=data.get("git_provider") or "github",
            repo_full_name=data.get("github_repo_full_name") or "",
            github_webhook_secret=data.get("github_webhook_secret") or "",
            github_token=data.get("github_token") or "",
            llm_provider_id=default_llm.id,
        )
    else:
        clear_webhook_secret = (
            "github_webhook_secret" in data and data["github_webhook_secret"] == ""
        )
        clear_github_token = "github_token" in data and data["github_token"] == ""
        repo = await repo_repo.update(
            repo.id,
            git_provider=data.get("git_provider"),
            repo_full_name=data.get("github_repo_full_name"),
            github_webhook_secret=data.get("github_webhook_secret"),
            github_token=data.get("github_token"),
            llm_provider_id=default_llm.id,
            clear_webhook_secret=clear_webhook_secret,
            clear_github_token=clear_github_token,
        )

    await sync_opencode_config_from_db(conn)
    row = await _legacy_row_from_multi(conn)
    if row is None:
        msg = "failed to load settings after update"
        raise RuntimeError(msg)
    logger.info("Integration settings updated (legacy API) at %s", row.updated_at)
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

    llm_repo = LlmProviderRepository(conn)
    repo_repo = RepoIntegrationRepository(conn)
    logger.info("Seeding settings from environment (one-time bootstrap)")

    default_llm = await llm_repo.create(
        name="Default",
        provider_id=env.llm_provider_id,
        base_url=env.llm_base_url,
        api_token=env.llm_api_token or "",
        model=env.llm_model,
        opencode_model=env.opencode_model or "",
        is_default=True,
    )
    await repo_repo.create(
        name="All repositories",
        git_provider="github",
        repo_full_name="",
        github_webhook_secret=env.github_webhook_secret or "",
        github_token=env.github_token or "",
        llm_provider_id=default_llm.id,
    )
    await sync_opencode_config_from_db(conn)
    multi = await _legacy_row_from_multi(conn)
    return multi if multi is not None else row


def _row_has_user_config(row: IntegrationSettingsRow) -> bool:
    return bool(
        row.github_webhook_secret
        or row.github_token
        or row.llm_api_token
        or row.github_repo_full_name
    )


def sync_opencode_config(
    row: IntegrationSettingsRow | None = None,
    output_path: Path | None = None,
) -> Path:
    """Deprecated sync helper; prefer sync_opencode_config_from_db."""
    from app.providers.opencode_config import build_opencode_config_from_integration_row

    config = build_opencode_config_from_integration_row(row) if row else {}
    if not config:
        infra = get_code_review_settings()
        from app.providers.opencode_config import build_opencode_config

        config = build_opencode_config(infra)
    path = output_path or DEFAULT_OPENCODE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def build_opencode_config_from_integration(
    integration: IntegrationSettingsRow,
    infra: CodeReviewSettings | None = None,
) -> dict:
    from app.providers.opencode_config import build_opencode_config_from_integration_row

    infra = infra or get_code_review_settings()
    return build_opencode_config_from_integration_row(integration, infra)


__all__ = [
    "build_providers_config",
    "get_integration_settings",
    "sync_opencode_config",
    "to_response",
    "update_integration_settings",
]
