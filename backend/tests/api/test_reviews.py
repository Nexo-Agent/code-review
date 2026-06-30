import hashlib
import hmac
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
from app.repositories.review_analytics import ReviewMetricAnalyticsRow
from app.repositories.teams import DEFAULT_TEAM_ID
from tests.conftest import make_dev_user, make_effective_permissions, make_review_row


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
            permissions=make_effective_permissions(
                dev_user,
                [DEFAULT_TEAM_ID],
            ),
        )

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_auth_context] = override_auth_context
    transport = ASGITransport(app=app)
    with patch(
        "app.api.v1.reviews.assert_review_access",
        new_callable=AsyncMock,
    ):
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
        base_url="https://api.example.com/v1",
        api_token="sk-test",
        model="gpt-4o",
        opencode_model="",
        is_default=True,
        enabled=True,
        created_at=now,
        updated_at=now,
    )


def _repo_row(llm: LlmProviderRow) -> RepoIntegrationRow:
    now = datetime.now(UTC)
    return RepoIntegrationRow(
        id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        name="owner/repo",
        git_provider="github",
        repo_full_name="owner/repo",
        llm_provider_id=None,
        github_webhook_secret="webhook-secret",
        github_token="gh-token",
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
        bitbucket_dc_base_url="",
        bitbucket_dc_token="",
        bitbucket_dc_webhook_username="",
        bitbucket_dc_webhook_password="",
        created_at=now,
        updated_at=now,
    )


def _sign_payload(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_github_webhook_uses_repo_integration(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _repo_row(llm)
    secret = repo_integration.github_webhook_secret
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

    review_row = make_review_row(
        provider="github",
        repo_full_name="owner/repo",
        pr_number=42,
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
        patch("app.api.v1.webhooks.run_review") as mock_task,
        patch("app.api.v1.webhooks.ReviewRepository", return_value=mock_repo),
    ):
        mock_task.delay = MagicMock()
        response = await client.post(
            f"/api/v1/webhooks/github/{repo_integration.id}",
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
async def test_github_webhook_legacy_endpoint_deprecated(client: AsyncClient) -> None:
    body = json.dumps(
        {
            "action": "opened",
            "pull_request": {"number": 1, "head": {"sha": "a" * 40}},
            "repository": {"full_name": "owner/repo"},
        }
    ).encode()

    response = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign_payload(body, "secret"),
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 410


@pytest.mark.asyncio
async def test_github_webhook_records_analytics_only_event(client: AsyncClient) -> None:
    llm = _llm_row()
    repo_integration = _repo_row(llm)
    secret = repo_integration.github_webhook_secret
    payload = {
        "action": "ready_for_review",
        "pull_request": {
            "id": 999,
            "number": 42,
            "head": {"sha": "abc123" * 5 + "ab"},
            "updated_at": "2026-06-30T10:00:00Z",
            "draft": False,
            "merged": False,
        },
        "sender": {"login": "alice", "type": "User"},
        "repository": {"full_name": "owner/repo"},
    }
    body = json.dumps(payload).encode()
    delivery_id = str(uuid4())

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
            AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.webhooks.ingest_provider_analytics_event",
            AsyncMock(return_value=1),
        ) as ingest_mock,
    ):
        response = await client.post(
            f"/api/v1/webhooks/github/{repo_integration.id}",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": _sign_payload(body, secret),
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    assert response.json()["detail"] == "analytics event recorded"
    ingest_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_review_fallback_pr_url_when_empty(client: AsyncClient) -> None:
    review_id = uuid4()
    review = make_review_row(id=review_id, pr_url="")
    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=review)
    mock_repo.list_findings = AsyncMock(return_value=[])

    from coreview_shared.git.github import GitHubProvider

    mock_bundle = MagicMock()
    mock_bundle.git = GitHubProvider(token="")

    with (
        patch("app.api.v1.reviews.ReviewRepository", return_value=mock_repo),
        patch(
            "app.api.v1.reviews.build_providers_for_repo",
            AsyncMock(return_value=mock_bundle),
        ),
    ):
        response = await client.get(f"/api/v1/reviews/{review_id}")

    assert response.status_code == 200
    assert response.json()["pr_url"] == "https://github.com/org/repo/pull/42"


@pytest.mark.asyncio
async def test_get_reviews_analytics_snapshot(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    metric_row = ReviewMetricAnalyticsRow(
        id=uuid4(),
        metric_key="helpful_rate",
        provider="github",
        granularity="rolling_window",
        window_start=now,
        window_end=now,
        dimension_key="all",
        repo_integration_id=None,
        team_id=None,
        repo_full_name="",
        metric_value_num=0.75,
        numerator=3.0,
        denominator=4.0,
        sample_size=4,
        dimensions_json={"dimension_key": "all"},
        job_run_id=uuid4(),
        computed_at=now,
    )
    analytics_repo = AsyncMock()
    analytics_repo.list_latest_metric_rows = AsyncMock(return_value=[metric_row])

    with patch(
        "app.api.v1.reviews.ReviewAnalyticsRepository",
        return_value=analytics_repo,
    ):
        response = await client.get("/api/v1/reviews/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_run_id"] == str(metric_row.job_run_id)
    assert payload["items"][0]["metric_key"] == "helpful_rate"


@pytest.mark.asyncio
async def test_get_reviews_analytics_team_scope_filters_rows(
    client: AsyncClient,
) -> None:
    now = datetime.now(UTC)
    team_metric = ReviewMetricAnalyticsRow(
        id=uuid4(),
        metric_key="helpful_rate",
        provider="github",
        granularity="rolling_window",
        window_start=now,
        window_end=now,
        dimension_key=f"team:{DEFAULT_TEAM_ID}",
        repo_integration_id=None,
        team_id=DEFAULT_TEAM_ID,
        repo_full_name="",
        metric_value_num=0.75,
        numerator=3.0,
        denominator=4.0,
        sample_size=4,
        dimensions_json={"dimension_key": f"team:{DEFAULT_TEAM_ID}"},
        job_run_id=uuid4(),
        computed_at=now,
    )
    repo_metric = ReviewMetricAnalyticsRow(
        id=uuid4(),
        metric_key="helpful_rate",
        provider="github",
        granularity="rolling_window",
        window_start=now,
        window_end=now,
        dimension_key="repo:abc",
        repo_integration_id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        repo_full_name="owner/repo",
        metric_value_num=0.8,
        numerator=4.0,
        denominator=5.0,
        sample_size=5,
        dimensions_json={"dimension_key": "repo:abc"},
        job_run_id=team_metric.job_run_id,
        computed_at=now,
    )
    analytics_repo = AsyncMock()
    analytics_repo.list_latest_metric_rows = AsyncMock(
        return_value=[team_metric, repo_metric]
    )

    with patch(
        "app.api.v1.reviews.ReviewAnalyticsRepository",
        return_value=analytics_repo,
    ):
        response = await client.get(
            f"/api/v1/reviews/analytics?scope=team&team_id={DEFAULT_TEAM_ID}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2


@pytest.mark.asyncio
async def test_get_reviews_analytics_repo_scope_returns_empty_snapshot(
    client: AsyncClient,
) -> None:
    now = datetime.now(UTC)
    team_metric = ReviewMetricAnalyticsRow(
        id=uuid4(),
        metric_key="helpful_rate",
        provider="github",
        granularity="rolling_window",
        window_start=now,
        window_end=now,
        dimension_key=f"team:{DEFAULT_TEAM_ID}",
        repo_integration_id=None,
        team_id=DEFAULT_TEAM_ID,
        repo_full_name="",
        metric_value_num=0.75,
        numerator=3.0,
        denominator=4.0,
        sample_size=4,
        dimensions_json={"dimension_key": f"team:{DEFAULT_TEAM_ID}"},
        job_run_id=uuid4(),
        computed_at=now,
    )
    analytics_repo = AsyncMock()
    analytics_repo.list_latest_metric_rows = AsyncMock(return_value=[team_metric])

    with patch(
        "app.api.v1.reviews.ReviewAnalyticsRepository",
        return_value=analytics_repo,
    ):
        response = await client.get(
            "/api/v1/reviews/analytics"
            "?scope=repo&repo_integration_id=bc47ecb1-bdb2-4ad1-8f9f-48ecf34655ce"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_run_id"] == str(team_metric.job_run_id)
    assert payload["items"] == []


@pytest.mark.asyncio
async def test_get_reviews_analytics_history_returns_points_for_scope(
    client: AsyncClient,
) -> None:
    now = datetime.now(UTC)
    history_row = ReviewMetricAnalyticsRow(
        id=uuid4(),
        metric_key="ai_review_coverage",
        provider="github",
        granularity="rolling_window",
        window_start=now,
        window_end=now,
        dimension_key=f"repo:{uuid4()}",
        repo_integration_id=uuid4(),
        team_id=DEFAULT_TEAM_ID,
        repo_full_name="owner/repo",
        metric_value_num=0.6,
        numerator=3.0,
        denominator=5.0,
        sample_size=5,
        dimensions_json={"dimension_key": "repo"},
        job_run_id=uuid4(),
        computed_at=now,
    )
    analytics_repo = AsyncMock()
    analytics_repo.list_metric_history = AsyncMock(return_value=[history_row])

    with patch(
        "app.api.v1.reviews.ReviewAnalyticsRepository",
        return_value=analytics_repo,
    ):
        response = await client.get(
            "/api/v1/reviews/analytics/history"
            f"?metric_key=ai_review_coverage&scope=repo&repo_integration_id={history_row.repo_integration_id}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric_key"] == "ai_review_coverage"
    assert payload["scope"] == "repo"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["metric_value_num"] == 0.6


@pytest.mark.asyncio
async def test_get_reviews_analytics_history_rejects_invalid_date_range(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/reviews/analytics/history"
        "?metric_key=helpful_rate&start=2026-06-30T00:00:00Z&end=2026-06-01T00:00:00Z"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "start must be before end"
