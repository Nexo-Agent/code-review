from datetime import UTC, datetime
from uuid import uuid4

from app.config import ReviewRuntimeConfig
from app.providers.opencode_config import build_opencode_config_from_llm_providers
from app.repositories.llm_providers import LlmProviderRow
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.teams import DEFAULT_TEAM_ID


def _llm_row() -> LlmProviderRow:
    now = datetime.now(UTC)
    return LlmProviderRow(
        id=uuid4(),
        organization_id=DEFAULT_ORG_ID,
        name="Default",
        provider_id="openai-compat",
        base_url="https://llm.example.com/v1",
        api_token="sk-abc",
        model="my-model",
        opencode_model="",
        is_default=True,
        enabled=True,
        created_at=now,
        updated_at=now,
    )


def _repo_row() -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="acme/app",
        git_provider="github",
        repo_full_name="acme/app",
        llm_provider_id=None,
        github_webhook_secret="secret",
        github_token="token",
        system_prompt="",
        enabled=True,
        ado_organization="",
        ado_project="",
        ado_pat="",
        ado_webhook_username="",
        ado_webhook_password="",
        created_at=now,
        updated_at=now,
    )


def test_build_opencode_config_from_llm_providers_literals() -> None:
    llm = _llm_row()
    config = build_opencode_config_from_llm_providers([llm], llm)
    provider = config["provider"]["openai-compat"]
    assert provider["options"]["baseURL"] == "https://llm.example.com/v1"
    assert provider["options"]["apiKey"] == "sk-abc"


def test_review_runtime_config_overlay() -> None:
    llm = _llm_row()
    repo = _repo_row()
    cfg = ReviewRuntimeConfig(
        git_provider=repo.git_provider,
        github_webhook_secret=repo.github_webhook_secret,
        github_token=repo.github_token,
        llm_provider_id=llm.provider_id,
        llm_base_url=llm.base_url,
        llm_api_token=llm.api_token,
        llm_model=llm.model,
        opencode_model=llm.opencode_model,
    )
    assert cfg.github_token == "token"
    assert cfg.llm_base_url == "https://llm.example.com/v1"
    assert cfg.resolved_opencode_model == "openai-compat/my-model"


def test_review_runtime_config_resolved_opencode_model_override() -> None:
    cfg = ReviewRuntimeConfig(
        git_provider="github",
        github_webhook_secret="",
        github_token="",
        llm_provider_id="openai-compat",
        llm_base_url="https://api.openai.com/v1",
        llm_api_token="",
        llm_model="gpt-4o",
        opencode_model="custom/other",
    )
    assert cfg.resolved_opencode_model == "custom/other"


def test_repo_integration_matches_repo() -> None:
    repo = _repo_row()
    assert repo.matches_repo("acme/app") is True
    assert repo.matches_repo("other/app") is False

    catch_all = RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="All",
        git_provider="github",
        repo_full_name="",
        llm_provider_id=None,
        github_webhook_secret="",
        github_token="",
        system_prompt="",
        enabled=True,
        ado_organization="",
        ado_project="",
        ado_pat="",
        ado_webhook_username="",
        ado_webhook_password="",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert catch_all.matches_repo("any/repo") is True
