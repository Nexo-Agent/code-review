from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context, get_current_user
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.usage import UsageBreakdownRow, UsageHistoryPoint, UsageSummary
from tests.conftest import make_dev_user, make_effective_permissions


@pytest_asyncio.fixture
async def app_client():
    app = create_app()
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, client, mock_conn
    app.dependency_overrides.clear()


def _set_auth(app, *, user) -> None:
    permissions = make_effective_permissions(user, [])

    async def override_auth_context():
        return AuthContext(
            user=user,
            accessible_team_ids=[],
            auth_enabled=True,
            permissions=permissions,
        )

    async def override_current_user():
        return user

    app.dependency_overrides[get_auth_context] = override_auth_context
    app.dependency_overrides[get_current_user] = override_current_user


async def _mock_require_permission(user, conn, action, *, team_id=None):
    if user.is_org_admin:
        return user
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail="Permission denied")


@pytest.mark.asyncio
async def test_get_usage_summary_requires_org_admin(app_client) -> None:
    app, client, _mock_conn = app_client
    member = make_dev_user(is_org_admin=False)
    _set_auth(app, user=member)

    with patch(
        "app.auth.dependencies.require_permission",
        side_effect=_mock_require_permission,
    ):
        response = await client.get("/api/v1/usage/summary")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_usage_summary_returns_totals(app_client) -> None:
    app, client, _mock_conn = app_client
    admin = make_dev_user(is_org_admin=True)
    _set_auth(app, user=admin)

    mock_repo = AsyncMock()
    mock_repo.query_summary.return_value = UsageSummary(
        total_tokens=1500,
        input_tokens=1200,
        output_tokens=300,
        llm_call_count=4,
        review_count=2,
    )

    with patch(
        "app.auth.dependencies.require_permission",
        side_effect=_mock_require_permission,
    ):
        with patch(
            "app.api.v1.usage.UsageRepository",
            lambda _conn: mock_repo,
        ):
            response = await client.get(
                "/api/v1/usage/summary",
                params={"team_id": str(UUID(int=1))},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_tokens"] == 1500
    assert payload["llm_call_count"] == 4
    assert "window_start" in payload
    assert payload["window_end"] >= payload["window_start"]


@pytest.mark.asyncio
async def test_get_usage_history_supports_metric_filter(app_client) -> None:
    app, client, _mock_conn = app_client
    admin = make_dev_user(is_org_admin=True)
    _set_auth(app, user=admin)
    now = datetime.now(tz=UTC)

    mock_repo = AsyncMock()
    mock_repo.query_history.return_value = [
        UsageHistoryPoint(
            window_start=now,
            window_end=now,
            metric_value_num=500.0,
            sample_size=2,
        )
    ]

    with patch(
        "app.auth.dependencies.require_permission",
        side_effect=_mock_require_permission,
    ):
        with patch(
            "app.api.v1.usage.UsageRepository",
            lambda _conn: mock_repo,
        ):
            response = await client.get(
                "/api/v1/usage/history",
                params={"metric": "input_tokens", "git_provider": "github"},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metric_key"] == "input_tokens"
    assert len(payload["points"]) == 1
    mock_repo.query_history.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_usage_breakdown_returns_rows(app_client) -> None:
    app, client, _mock_conn = app_client
    admin = make_dev_user(is_org_admin=True)
    _set_auth(app, user=admin)

    mock_repo = AsyncMock()
    mock_repo.query_breakdown.return_value = [
        UsageBreakdownRow(
            dimension_id="team-1",
            dimension_label="Platform",
            review_count=2,
            llm_call_count=4,
            input_tokens=900,
            output_tokens=300,
            total_tokens=1200,
            percent_of_total=100.0,
        )
    ]

    with patch(
        "app.auth.dependencies.require_permission",
        side_effect=_mock_require_permission,
    ):
        with patch(
            "app.api.v1.usage.UsageRepository",
            lambda _conn: mock_repo,
        ):
            response = await client.get(
                "/api/v1/usage/breakdown",
                params={"group_by": "team"},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["group_by"] == "team"
    assert payload["items"][0]["dimension_label"] == "Platform"
