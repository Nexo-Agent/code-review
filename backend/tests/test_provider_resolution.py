from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.llm_providers import LlmProviderRow
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.teams import DEFAULT_TEAM_ID, TeamRow
from app.services.provider_resolution import resolve_llm_provider_for_repo


def _repo_row(*, llm_provider_id=None) -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="acme/app",
        git_provider="github",
        repo_full_name="acme/app",
        llm_provider_id=llm_provider_id,
        github_webhook_secret="secret",
        github_token="token",
        system_prompt="",
        enabled=True,
        ado_organization="",
        ado_project="",
        ado_pat="",
        ado_webhook_username="",
        ado_webhook_password="",
        gitlab_base_url="",
        gitlab_token="",
        gitlab_webhook_secret="",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_resolve_llm_provider_uses_repo_selection() -> None:
    llm_id = uuid4()
    repo_llm = LlmProviderRow(
        id=llm_id,
        organization_id=DEFAULT_ORG_ID,
        name="Repo LLM",
        provider_id="openai-compat",
        base_url="https://llm.example.com/v1",
        api_token="sk-test",
        model="gpt-4o",
        opencode_model="",
        is_default=False,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    team = TeamRow(
        id=DEFAULT_TEAM_ID,
        organization_id=DEFAULT_ORG_ID,
        name="Default Team",
        slug="default",
        created_at=datetime.now(UTC),
    )

    mock_conn = AsyncMock()
    team_repo = MagicMock()
    team_repo.get = AsyncMock(return_value=team)
    llm_repo = MagicMock()
    llm_repo.get = AsyncMock(return_value=repo_llm)
    llm_repo.get_default = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.provider_resolution.TeamRepository",
            lambda conn: team_repo,
        )
        mp.setattr(
            "app.services.provider_resolution.LlmProviderRepository",
            lambda conn: llm_repo,
        )
        resolved = await resolve_llm_provider_for_repo(
            mock_conn,
            _repo_row(llm_provider_id=llm_id),
        )

    assert resolved is repo_llm
    llm_repo.get.assert_awaited_once_with(llm_id)
    llm_repo.get_default.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_llm_provider_falls_back_to_org_default() -> None:
    default_llm = LlmProviderRow(
        id=uuid4(),
        organization_id=DEFAULT_ORG_ID,
        name="Default",
        provider_id="openai-compat",
        base_url="https://llm.example.com/v1",
        api_token="sk-test",
        model="gpt-4o",
        opencode_model="",
        is_default=True,
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    team = TeamRow(
        id=DEFAULT_TEAM_ID,
        organization_id=DEFAULT_ORG_ID,
        name="Default Team",
        slug="default",
        created_at=datetime.now(UTC),
    )

    mock_conn = AsyncMock()
    team_repo = MagicMock()
    team_repo.get = AsyncMock(return_value=team)
    llm_repo = MagicMock()
    llm_repo.get_default = AsyncMock(return_value=default_llm)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.provider_resolution.TeamRepository",
            lambda conn: team_repo,
        )
        mp.setattr(
            "app.services.provider_resolution.LlmProviderRepository",
            lambda conn: llm_repo,
        )
        resolved = await resolve_llm_provider_for_repo(
            mock_conn,
            _repo_row(),
        )

    assert resolved is default_llm
