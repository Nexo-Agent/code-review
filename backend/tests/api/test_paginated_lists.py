from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context, get_current_user
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.teams import DEFAULT_TEAM_ID
from app.schemas.llm_provider import LlmProviderListResponse, LlmProviderResponse
from app.schemas.repo_integration import (
    OrgRepositoryListResponse,
    OrgRepositoryResponse,
)
from app.schemas.team import TeamListResponse, TeamResponse
from tests.conftest import make_dev_user


@pytest.fixture
async def client() -> AsyncClient:
    app = create_app()
    mock_conn = AsyncMock()
    dev_user = make_dev_user()

    async def override_get_conn():
        yield mock_conn

    async def override_auth_context():
        return AuthContext(
            user=dev_user,
            accessible_team_ids=[DEFAULT_TEAM_ID],
            auth_enabled=False,
        )

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_current_user] = lambda: dev_user
    app.dependency_overrides[get_auth_context] = override_auth_context
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_teams_paginated(client: AsyncClient) -> None:
    team_id = uuid4()
    org_id = uuid4()
    now = datetime.now(tz=UTC)

    with patch(
        "app.api.v1.teams.list_teams_paginated",
        new_callable=AsyncMock,
    ) as list_teams:
        list_teams.return_value = TeamListResponse(
            items=[
                TeamResponse(
                    id=team_id,
                    organization_id=org_id,
                    name="Default Team",
                    slug="default",
                    repo_count=2,
                    member_count=3,
                    created_at=now,
                )
            ],
            total=1,
        )
        response = await client.get("/api/v1/teams?limit=20&offset=0&q=default")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "default"
    list_teams.assert_awaited_once()
    call_kwargs = list_teams.await_args.kwargs
    assert call_kwargs["search"] == "default"
    assert call_kwargs["limit"] == 20
    assert call_kwargs["offset"] == 0


@pytest.mark.asyncio
async def test_list_org_repositories_paginated(client: AsyncClient) -> None:
    repo_id = uuid4()
    team_id = DEFAULT_TEAM_ID
    now = datetime.now(tz=UTC)

    with patch(
        "app.api.v1.org_repositories.list_repo_integrations_for_teams_paginated",
        new_callable=AsyncMock,
    ) as list_repos:
        list_repos.return_value = OrgRepositoryListResponse(
            items=[
                OrgRepositoryResponse(
                    id=repo_id,
                    team_id=team_id,
                    name="My Repo",
                    git_provider="github",
                    repo_full_name="owner/repo",
                    llm_provider_id=None,
                    llm_provider_name=None,
                    system_prompt="",
                    enabled=True,
                    github_webhook_secret_configured=True,
                    github_token_configured=True,
                    ado_organization="",
                    ado_project="",
                    ado_pat_configured=False,
                    ado_webhook_configured=False,
                    gitlab_base_url="",
                    gitlab_token_configured=False,
                    gitlab_webhook_secret_configured=False,
                    webhook_url="http://example.com/webhook",
                    created_at=now,
                    updated_at=now,
                    team_name="Default Team",
                )
            ],
            total=1,
        )
        response = await client.get(
            "/api/v1/repositories?q=repo&enabled=true&git_provider=github"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["repo_full_name"] == "owner/repo"
    list_repos.assert_awaited_once()
    call_kwargs = list_repos.await_args.kwargs
    assert call_kwargs["search"] == "repo"
    assert call_kwargs["enabled"] is True
    assert call_kwargs["git_provider"] == "github"
    assert call_kwargs["limit"] == 20
    assert call_kwargs["offset"] == 0


@pytest.mark.asyncio
async def test_list_org_repositories_empty_without_team_access() -> None:
    app = create_app()
    mock_conn = AsyncMock()
    dev_user = make_dev_user()

    async def override_get_conn():
        yield mock_conn

    async def override_auth_context():
        return AuthContext(
            user=dev_user,
            accessible_team_ids=[],
            auth_enabled=False,
        )

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_auth_context] = override_auth_context
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/repositories")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_list_llm_providers_paginated(client: AsyncClient) -> None:
    provider_id = uuid4()
    now = datetime.now(tz=UTC)

    with patch(
        "app.api.v1.llm_providers.list_llm_providers_paginated",
        new_callable=AsyncMock,
    ) as list_providers:
        list_providers.return_value = LlmProviderListResponse(
            items=[
                LlmProviderResponse(
                    id=provider_id,
                    name="Default Provider",
                    provider_id="openai",
                    base_url="https://api.example.com/v1",
                    model="gpt-4",
                    opencode_model="",
                    resolved_opencode_model="openai/gpt-4",
                    is_default=True,
                    enabled=True,
                    api_token_configured=True,
                    created_at=now,
                    updated_at=now,
                )
            ],
            total=1,
        )
        response = await client.get("/api/v1/settings/llm-providers?q=default")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Default Provider"
    list_providers.assert_awaited_once()
    call_kwargs = list_providers.await_args.kwargs
    assert call_kwargs["search"] == "default"
    assert call_kwargs["limit"] == 20
    assert call_kwargs["offset"] == 0
