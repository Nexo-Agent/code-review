from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.llm_providers import LlmProviderRow
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.projects import DEFAULT_PROJECT_ID, ProjectRow
from app.repositories.teams import DEFAULT_TEAM_ID
from app.services.provider_resolution import resolve_llm_provider_for_project


@pytest.mark.asyncio
async def test_resolve_llm_provider_uses_project_selection() -> None:
    llm_id = uuid4()
    project_llm = LlmProviderRow(
        id=llm_id,
        organization_id=DEFAULT_ORG_ID,
        name="Project LLM",
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
    project = ProjectRow(
        id=DEFAULT_PROJECT_ID,
        team_id=DEFAULT_TEAM_ID,
        name="Default Project",
        description="",
        llm_provider_id=llm_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_conn = AsyncMock()
    project_repo = MagicMock()
    project_repo.get_with_team = AsyncMock(return_value=(project, DEFAULT_ORG_ID))
    llm_repo = MagicMock()
    llm_repo.get = AsyncMock(return_value=project_llm)
    llm_repo.get_default = AsyncMock(return_value=None)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.provider_resolution.ProjectRepository",
            lambda conn: project_repo,
        )
        mp.setattr(
            "app.services.provider_resolution.LlmProviderRepository",
            lambda conn: llm_repo,
        )
        resolved = await resolve_llm_provider_for_project(mock_conn, DEFAULT_PROJECT_ID)

    assert resolved is project_llm
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
    project = ProjectRow(
        id=DEFAULT_PROJECT_ID,
        team_id=DEFAULT_TEAM_ID,
        name="Default Project",
        description="",
        llm_provider_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_conn = AsyncMock()
    project_repo = MagicMock()
    project_repo.get_with_team = AsyncMock(return_value=(project, DEFAULT_ORG_ID))
    llm_repo = MagicMock()
    llm_repo.get_default = AsyncMock(return_value=default_llm)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.services.provider_resolution.ProjectRepository",
            lambda conn: project_repo,
        )
        mp.setattr(
            "app.services.provider_resolution.LlmProviderRepository",
            lambda conn: llm_repo,
        )
        resolved = await resolve_llm_provider_for_project(mock_conn, DEFAULT_PROJECT_ID)

    assert resolved is default_llm
