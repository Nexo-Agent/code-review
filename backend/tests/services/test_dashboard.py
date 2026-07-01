from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.auth.dependencies import AuthContext
from app.repositories.teams import DEFAULT_TEAM_ID
from app.repositories.usage import UsageSummary
from app.services.dashboard import get_dashboard_summary
from tests.conftest import make_dev_user, make_effective_permissions


@pytest.mark.asyncio
async def test_get_dashboard_summary_builds_usage_window_for_org_admin() -> None:
    user = make_dev_user()
    auth = AuthContext(
        user=user,
        accessible_team_ids=[DEFAULT_TEAM_ID],
        auth_enabled=False,
        permissions=make_effective_permissions(user, [DEFAULT_TEAM_ID]),
    )
    mock_conn = AsyncMock()

    review_repo = AsyncMock()
    review_repo.count_reviews_by_status = AsyncMock(
        return_value={"pending": 0, "running": 0, "completed": 1, "failed": 0}
    )
    review_repo.list_reviews = AsyncMock(return_value=[])

    team_repo = AsyncMock()
    team_repo.count_for_teams = AsyncMock(return_value=1)

    repo_repo = AsyncMock()
    repo_repo.count_for_teams = AsyncMock(return_value=2)

    user_repo = AsyncMock()
    user_repo.count = AsyncMock(return_value=3)

    llm_repo = AsyncMock()
    llm_repo.count = AsyncMock(return_value=1)

    idp_repo = AsyncMock()
    idp_repo.get = AsyncMock(return_value=None)

    usage_repo = AsyncMock()
    usage_repo.query_summary = AsyncMock(
        return_value=UsageSummary(
            total_tokens=100,
            input_tokens=60,
            output_tokens=40,
            llm_call_count=5,
            review_count=2,
        )
    )

    analytics_repo = AsyncMock()
    analytics_repo.list_latest_metric_rows = AsyncMock(return_value=[])

    with (
        patch("app.services.dashboard.ReviewRepository", return_value=review_repo),
        patch("app.services.dashboard.TeamRepository", return_value=team_repo),
        patch(
            "app.services.dashboard.RepoIntegrationRepository",
            return_value=repo_repo,
        ),
        patch("app.services.dashboard.UserRepository", return_value=user_repo),
        patch("app.services.dashboard.LlmProviderRepository", return_value=llm_repo),
        patch(
            "app.services.dashboard.IdentityProviderRepository",
            return_value=idp_repo,
        ),
        patch("app.services.dashboard.UsageRepository", return_value=usage_repo),
        patch(
            "app.services.dashboard.ReviewAnalyticsRepository",
            return_value=analytics_repo,
        ),
    ):
        result = await get_dashboard_summary(mock_conn, auth)

    assert result.capabilities.usage is True
    assert result.usage is not None
    assert result.usage.total_tokens == 100
    assert result.usage.window_start is not None
    assert result.usage.window_end is not None
    assert result.usage.window_start < result.usage.window_end

    usage_repo.query_summary.assert_awaited_once()
    filters = usage_repo.query_summary.await_args.args[0]
    assert filters.start is not None
    assert filters.end is not None


@pytest.mark.asyncio
async def test_get_dashboard_summary_empty_without_teams() -> None:
    user = make_dev_user(id=uuid4())
    auth = AuthContext(
        user=user,
        accessible_team_ids=[],
        auth_enabled=True,
        permissions=make_effective_permissions(user, []),
    )
    result = await get_dashboard_summary(AsyncMock(), auth)
    assert result.capabilities.reviews is False
    assert result.reviews.total == 0
