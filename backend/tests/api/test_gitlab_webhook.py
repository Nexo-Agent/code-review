import base64
import hashlib
import hmac
import json
import time
from dataclasses import replace
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


def _gitlab_repo_row(llm: LlmProviderRow) -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="acme/backend",
        git_provider="gitlab",
        repo_full_name="acme/backend",
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
        gitlab_base_url="https://gitlab.example.com",
        gitlab_token="glpat-test",
        gitlab_webhook_secret="hook-secret",
        bitbucket_token="",
        bitbucket_webhook_secret="",
        bitbucket_dc_base_url="",
        bitbucket_dc_token="",
        bitbucket_dc_webhook_username="",
        bitbucket_dc_webhook_password="",
        created_at=now,
        updated_at=now,
    )


def _gitlab_payload(*, action: str = "open") -> dict:
    return {
        "object_kind": "merge_request",
        "project": {"path_with_namespace": "acme/backend"},
        "object_attributes": {
            "id": 93,
            "iid": 16,
            "action": action,
            "title": "Add validation",
            "draft": False,
            "work_in_progress": False,
            "last_commit": {"id": "abc123" * 5 + "ab"},
        },
    }


def _signing_token() -> str:
    return "whsec_" + base64.b64encode(b"hook-signing-key").decode("utf-8")


def _sign_gitlab_webhook(
    body: bytes,
    signing_token: str,
    message_id: str,
) -> dict[str, str]:
    timestamp = str(int(time.time()))
    raw_key = base64.b64decode(signing_token.removeprefix("whsec_"))
    body_text = body.decode("utf-8")
    message = f"{message_id}.{timestamp}.{body_text}".encode()
    digest = hmac.new(raw_key, message, hashlib.sha256).digest()
    signature = "v1," + base64.b64encode(digest).decode("utf-8")
    return {
        "webhook-id": message_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": signature,
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_gitlab_webhook_enqueues_review_with_signing_token(
    client: AsyncClient,
) -> None:
    llm = _llm_row()
    repo_integration = replace(
        _gitlab_repo_row(llm),
        gitlab_webhook_secret=_signing_token(),
        bitbucket_token="",
        bitbucket_webhook_secret="",
        bitbucket_dc_base_url="",
        bitbucket_dc_token="",
        bitbucket_dc_webhook_username="",
        bitbucket_dc_webhook_password="",
    )
    payload = _gitlab_payload(action="open")
    body = json.dumps(payload).encode()
    delivery_id = "evt-sign-1"
    headers = _sign_gitlab_webhook(
        body,
        repo_integration.gitlab_webhook_secret,
        delivery_id,
    )
    headers["X-Gitlab-Event-UUID"] = delivery_id

    review_row = make_review_row(
        provider="gitlab",
        repo_full_name="acme/backend",
        pr_number=16,
        pr_title="Add validation",
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
            f"/api/v1/webhooks/gitlab/{repo_integration.id}",
            content=body,
            headers=headers,
        )

    assert response.status_code == 202
    run_review.delay.assert_called_once_with(str(review_row.id))


@pytest.mark.asyncio
async def test_gitlab_webhook_invalid_signing_token(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = replace(
        _gitlab_repo_row(llm),
        gitlab_webhook_secret=_signing_token(),
        bitbucket_token="",
        bitbucket_webhook_secret="",
        bitbucket_dc_base_url="",
        bitbucket_dc_token="",
        bitbucket_dc_webhook_username="",
        bitbucket_dc_webhook_password="",
    )
    body = json.dumps(_gitlab_payload()).encode()
    headers = _sign_gitlab_webhook(
        body,
        repo_integration.gitlab_webhook_secret,
        "evt-sign-2",
    )
    headers["webhook-signature"] = "v1,invalid"

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
            f"/api/v1/webhooks/gitlab/{repo_integration.id}",
            content=body,
            headers=headers,
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gitlab_webhook_returns_existing_for_duplicate_commit(
    client: AsyncClient,
) -> None:
    llm = _llm_row()
    repo_integration = _gitlab_repo_row(llm)
    payload = _gitlab_payload(action="open")
    body = json.dumps(payload).encode()
    delivery_id = "wh_duplicate"

    existing_review = make_review_row(
        provider="gitlab",
        repo_full_name="acme/backend",
        pr_number=16,
        pr_title="Add validation",
        head_sha="abc123" * 5 + "ab",
        delivery_id="wh_original",
        repo_integration_id=repo_integration.id,
        created_at=datetime.now(UTC),
    )

    mock_repo = MagicMock()
    mock_repo.get_by_delivery_id = AsyncMock(return_value=None)
    mock_repo.get_by_repo_pr_sha = AsyncMock(return_value=existing_review)
    mock_repo.create = AsyncMock()

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
            f"/api/v1/webhooks/gitlab/{repo_integration.id}",
            content=body,
            headers={
                "X-Gitlab-Token": "hook-secret",
                "webhook-id": delivery_id,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    assert response.json()["id"] == str(existing_review.id)
    mock_repo.create.assert_not_called()
    run_review.delay.assert_not_called()


@pytest.mark.asyncio
async def test_gitlab_webhook_enqueues_review(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _gitlab_repo_row(llm)
    payload = _gitlab_payload(action="open")
    body = json.dumps(payload).encode()
    delivery_id = "evt-123"

    review_row = make_review_row(
        provider="gitlab",
        repo_full_name="acme/backend",
        pr_number=16,
        pr_title="Add validation",
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
            f"/api/v1/webhooks/gitlab/{repo_integration.id}",
            content=body,
            headers={
                "X-Gitlab-Token": "hook-secret",
                "X-Gitlab-Event-UUID": delivery_id,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    run_review.delay.assert_called_once_with(str(review_row.id))


@pytest.mark.asyncio
async def test_gitlab_webhook_invalid_token(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _gitlab_repo_row(llm)
    body = json.dumps(_gitlab_payload()).encode()

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
            f"/api/v1/webhooks/gitlab/{repo_integration.id}",
            content=body,
            headers={
                "X-Gitlab-Token": "wrong-secret",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gitlab_webhook_ignores_merge(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _gitlab_repo_row(llm)
    body = json.dumps(_gitlab_payload(action="merge")).encode()

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
            f"/api/v1/webhooks/gitlab/{repo_integration.id}",
            content=body,
            headers={
                "X-Gitlab-Token": "hook-secret",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    assert response.json()["detail"] == "event ignored"
    run_review.delay.assert_not_called()
