import base64
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
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


def _ado_repo_row(llm: LlmProviderRow) -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="fabrikam/MyProject/Repo",
        git_provider="azure-devops",
        repo_full_name="fabrikam/MyProject/Repo",
        llm_provider_id=None,
        github_webhook_secret="",
        github_token="",
        system_prompt="",
        enabled=True,
        ado_organization="fabrikam",
        ado_project="MyProject",
        ado_pat="ado-pat",
        ado_webhook_username="hook-user",
        ado_webhook_password="hook-pass",
        gitlab_base_url="",
        gitlab_token="",
        gitlab_webhook_secret="",
        created_at=now,
        updated_at=now,
    )


def _ado_payload() -> dict:
    return {
        "id": str(uuid4()),
        "eventType": "git.pullrequest.created",
        "resource": {
            "repository": {
                "id": "repo-guid",
                "name": "Repo",
                "project": {"name": "MyProject"},
            },
            "pullRequestId": 42,
            "status": "active",
            "title": "Add feature",
            "lastMergeSourceCommit": {"commitId": "abc123" * 5 + "ab"},
        },
        "resourceContainers": {
            "account": {"baseUrl": "https://dev.azure.com/fabrikam/"}
        },
    }


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


@pytest.mark.asyncio
async def test_ado_webhook_enqueues_review(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _ado_repo_row(llm)
    payload = _ado_payload()
    body = json.dumps(payload).encode()
    delivery_id = payload["id"]

    review_row = make_review_row(
        provider="azure-devops",
        repo_full_name="fabrikam/MyProject/Repo",
        pr_number=42,
        pr_title="Add feature",
        head_sha="abc123" * 5 + "ab",
        delivery_id=delivery_id,
        repo_integration_id=repo_integration.id,
        created_at=datetime.now(UTC),
    )

    mock_repo = MagicMock()
    mock_repo.get_by_delivery_id = AsyncMock(return_value=None)
    mock_repo.get_by_repo_pr_sha = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(return_value=review_row)

    mock_integration_repo = MagicMock()
    mock_integration_repo.get_with_team = AsyncMock(
        return_value=(repo_integration, DEFAULT_TEAM_ID)
    )

    with (
        patch(
            "app.api.v1.webhooks.RepoIntegrationRepository",
            return_value=mock_integration_repo,
        ),
        patch(
            "app.api.v1.webhooks.resolve_llm_provider_for_repo",
            AsyncMock(return_value=llm),
        ),
        patch("app.api.v1.webhooks.ReviewRepository", return_value=mock_repo),
        patch("app.api.v1.webhooks.run_review") as run_review,
    ):
        run_review.delay = MagicMock()
        response = await client.post(
            f"/api/v1/webhooks/azure-devops/{repo_integration.id}",
            content=body,
            headers={
                "Authorization": _basic_auth_header("hook-user", "hook-pass"),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    run_review.delay.assert_called_once_with(str(review_row.id))


@pytest.mark.asyncio
async def test_ado_webhook_invalid_auth(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _ado_repo_row(llm)
    body = json.dumps(_ado_payload()).encode()

    mock_integration_repo = MagicMock()
    mock_integration_repo.get_with_team = AsyncMock(
        return_value=(repo_integration, DEFAULT_TEAM_ID)
    )

    with (
        patch(
            "app.api.v1.webhooks.RepoIntegrationRepository",
            return_value=mock_integration_repo,
        ),
        patch(
            "app.api.v1.webhooks.resolve_llm_provider_for_repo",
            AsyncMock(return_value=llm),
        ),
    ):
        response = await client.post(
            f"/api/v1/webhooks/azure-devops/{repo_integration.id}",
            content=body,
            headers={
                "Authorization": _basic_auth_header("wrong", "creds"),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ado_webhook_ignores_completed(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _ado_repo_row(llm)
    payload = _ado_payload()
    payload["eventType"] = "git.pullrequest.updated"
    payload["resource"]["status"] = "completed"
    body = json.dumps(payload).encode()

    mock_integration_repo = MagicMock()
    mock_integration_repo.get_with_team = AsyncMock(
        return_value=(repo_integration, DEFAULT_TEAM_ID)
    )

    with (
        patch(
            "app.api.v1.webhooks.RepoIntegrationRepository",
            return_value=mock_integration_repo,
        ),
        patch(
            "app.api.v1.webhooks.resolve_llm_provider_for_repo",
            AsyncMock(return_value=llm),
        ),
        patch("app.api.v1.webhooks.run_review") as run_review,
    ):
        run_review.delay = MagicMock()
        response = await client.post(
            f"/api/v1/webhooks/azure-devops/{repo_integration.id}",
            content=body,
            headers={
                "Authorization": _basic_auth_header("hook-user", "hook-pass"),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    assert response.json()["detail"] == "event ignored"
    run_review.delay.assert_not_called()
