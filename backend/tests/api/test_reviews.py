import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_conn
from app.main import create_app
from app.repositories.integration_settings import IntegrationSettingsRow
from app.repositories.reviews import ReviewRow


@pytest.fixture
async def client() -> AsyncClient:
    app = create_app()
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _integration_row(**overrides: object) -> IntegrationSettingsRow:
    now = datetime.now(UTC)
    defaults = {
        "git_provider": "github",
        "github_repo_full_name": "owner/repo",
        "github_webhook_secret": "webhook-secret",
        "github_token": "gh-token",
        "llm_provider_id": "openai-compat",
        "llm_base_url": "https://api.example.com/v1",
        "llm_api_token": "sk-test",
        "llm_model": "gpt-4o",
        "opencode_model": "",
        "updated_at": now,
    }
    defaults.update(overrides)
    return IntegrationSettingsRow(**defaults)


def _sign_payload(payload: bytes, secret: str) -> str:
    return (
        "sha256="
        + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    )


@pytest.mark.asyncio
async def test_github_webhook_uses_db_settings(client: AsyncClient) -> None:
    integration = _integration_row()
    secret = integration.github_webhook_secret
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "head": {"sha": "abc123" * 5 + "ab"},
        },
        "repository": {"full_name": "owner/repo"},
    }
    body = json.dumps(payload).encode()
    delivery_id = str(uuid4())

    review_row = ReviewRow(
        id=uuid4(),
        provider="github",
        repo_full_name="owner/repo",
        pr_number=42,
        head_sha="abc123" * 5 + "ab",
        status="pending",
        delivery_id=delivery_id,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(UTC),
    )

    mock_repo = MagicMock()
    mock_repo.get_by_delivery_id = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(return_value=review_row)

    with (
        patch(
            "app.api.v1.webhooks.get_integration_settings",
            AsyncMock(return_value=integration),
        ),
        patch("app.api.v1.webhooks.run_review") as mock_task,
        patch("app.api.v1.webhooks.ReviewRepository", return_value=mock_repo),
    ):
        mock_task.delay = MagicMock()
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": _sign_payload(body, secret),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_github_webhook_rejects_unconfigured_repo(client: AsyncClient) -> None:
    integration = _integration_row(github_repo_full_name="other/repo")
    body = json.dumps(
        {
            "action": "opened",
            "pull_request": {"number": 1, "head": {"sha": "a" * 40}},
            "repository": {"full_name": "owner/repo"},
        }
    ).encode()

    signature = _sign_payload(body, integration.github_webhook_secret)
    with patch(
        "app.api.v1.webhooks.get_integration_settings",
        AsyncMock(return_value=integration),
    ):
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    assert response.json()["detail"] == "repository not configured for review"
