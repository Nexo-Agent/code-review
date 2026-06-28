import base64
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.llm_providers import LlmProviderRow
from app.repositories.organizations import DEFAULT_ORG_ID
from app.repositories.repo_integrations import RepoIntegrationRow
from app.repositories.teams import DEFAULT_TEAM_ID
from tests.conftest import make_dev_user, make_review_row


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
    app.dependency_overrides[get_auth_context] = override_auth_context
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _llm_row() -> LlmProviderRow:
    now = datetime.now(UTC)
    return LlmProviderRow(
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
        created_at=now,
        updated_at=now,
    )


def _bitbucket_dc_repo_row(llm: LlmProviderRow) -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="ACME/backend",
        git_provider="bitbucket-dc",
        repo_full_name="ACME/backend",
        llm_provider_id=llm.id,
        github_webhook_secret="",
        github_token="",
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
        bitbucket_token="",
        bitbucket_webhook_secret="",
        bitbucket_dc_base_url="https://bitbucket.example.com",
        bitbucket_dc_token="dc-token",
        bitbucket_dc_webhook_username="hook-user",
        bitbucket_dc_webhook_password="hook-pass",
        created_at=now,
        updated_at=now,
    )


def _payload() -> dict:
    return {
        "pullRequest": {
            "id": 9,
            "title": "Feature",
            "state": "OPEN",
            "fromRef": {"latestCommit": "abc123" * 5 + "ab"},
            "toRef": {
                "repository": {
                    "slug": "backend",
                    "project": {"key": "ACME"},
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_bitbucket_dc_webhook_enqueues_review(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_row = _bitbucket_dc_repo_row(llm)
    body = json.dumps(_payload()).encode()
    auth = base64.b64encode(b"hook-user:hook-pass").decode()

    with (
        patch(
            "app.api.v1.webhooks.RepoIntegrationRepository.get_with_team",
            new_callable=AsyncMock,
            return_value=(repo_row, DEFAULT_TEAM_ID),
        ),
        patch(
            "app.api.v1.webhooks.resolve_llm_provider_for_repo",
            new_callable=AsyncMock,
            return_value=llm,
        ),
        patch(
            "app.api.v1.webhooks.ReviewRepository.get_by_delivery_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.v1.webhooks.ReviewRepository.get_by_repo_pr_sha",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.v1.webhooks.ReviewRepository.create",
            new_callable=AsyncMock,
            return_value=make_review_row(repo_integration_id=repo_row.id),
        ),
        patch("app.api.v1.webhooks.run_review.delay") as mock_delay,
    ):
        response = await client.post(
            f"/api/v1/webhooks/bitbucket-dc/{repo_row.id}",
            content=body,
            headers={
                "X-Event-Key": "pr:opened",
                "Authorization": f"Basic {auth}",
            },
        )

    assert response.status_code == 202
    mock_delay.assert_called_once()
