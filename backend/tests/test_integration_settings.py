
from datetime import UTC, datetime

from app.repositories.integration_settings import IntegrationSettingsRow
from app.services.integration_settings import (
    build_opencode_config_from_integration,
    build_providers_config,
    to_response,
)


def _row() -> IntegrationSettingsRow:
    return IntegrationSettingsRow(
        git_provider="github",
        github_repo_full_name="acme/app",
        github_webhook_secret="secret",
        github_token="token",
        llm_provider_id="openai-compat",
        llm_base_url="https://llm.example.com/v1",
        llm_api_token="sk-abc",
        llm_model="my-model",
        opencode_model="",
        updated_at=datetime.now(UTC),
    )


def test_to_response_masks_secrets() -> None:
    response = to_response(_row())
    assert response.github_token_configured is True
    assert response.llm_api_token_configured is True
    assert response.github_webhook_secret_configured is True
    assert response.resolved_opencode_model == "openai-compat/my-model"


def test_build_opencode_config_from_integration_literals() -> None:
    config = build_opencode_config_from_integration(_row())
    provider = config["provider"]["openai-compat"]
    assert provider["options"]["baseURL"] == "https://llm.example.com/v1"
    assert provider["options"]["apiKey"] == "sk-abc"


def test_build_providers_config_overlay() -> None:
    cfg = build_providers_config(_row())
    assert cfg.github_token == "token"
    assert cfg.llm_base_url == "https://llm.example.com/v1"
    assert cfg.resolved_opencode_model == "openai-compat/my-model"


def test_accepts_repo_filter() -> None:
    row = _row()
    assert row.accepts_repo("acme/app") is True
    assert row.accepts_repo("other/app") is False
    empty = IntegrationSettingsRow(
        git_provider="github",
        github_repo_full_name="",
        github_webhook_secret="",
        github_token="",
        llm_provider_id="openai-compat",
        llm_base_url="https://api.openai.com/v1",
        llm_api_token="",
        llm_model="gpt-4o",
        opencode_model="",
        updated_at=datetime.now(UTC),
    )
    assert empty.accepts_repo("any/repo") is True
