from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.teams import DEFAULT_TEAM_ID
from app.schemas.dashboard import (
    DashboardAnalyticsSection,
    DashboardCapabilities,
    DashboardOnboardingSection,
    DashboardOnboardingStep,
    DashboardResourcesSection,
    DashboardReviewsSection,
    DashboardReviewStatusCounts,
    DashboardSummaryResponse,
)
from tests.conftest import make_dev_user, make_effective_permissions


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
            permissions=make_effective_permissions(dev_user, [DEFAULT_TEAM_ID]),
        )

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_auth_context] = override_auth_context
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_dashboard_summary_returns_role_aware_payload(
    client: AsyncClient,
) -> None:
    summary = DashboardSummaryResponse(
        capabilities=DashboardCapabilities(
            reviews=True,
            resources=True,
            onboarding=True,
            analytics=True,
            usage=True,
        ),
        reviews=DashboardReviewsSection(
            total=1,
            by_status=DashboardReviewStatusCounts(completed=1),
            recent=[],
        ),
        resources=DashboardResourcesSection(
            teams=1,
            repositories=2,
            users=3,
            llm_providers=1,
        ),
        onboarding=DashboardOnboardingSection(
            steps=[
                DashboardOnboardingStep(
                    key="first_review",
                    label="Run your first review",
                    done=True,
                )
            ],
            all_complete=True,
        ),
        analytics=DashboardAnalyticsSection(
            scope="all",
            metrics=[],
        ),
    )

    with patch(
        "app.api.v1.dashboard.get_dashboard_summary",
        new=AsyncMock(return_value=summary),
    ):
        response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["capabilities"]["reviews"] is True
    assert data["capabilities"]["usage"] is True
    assert data["reviews"]["total"] == 1
    assert data["resources"]["users"] == 3


@pytest.mark.asyncio
async def test_get_dashboard_summary_hides_org_sections_for_member(
    client: AsyncClient,
) -> None:
    member = make_dev_user(is_org_admin=False)
    app = create_app()
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    async def override_auth_context():
        return AuthContext(
            user=member,
            accessible_team_ids=[DEFAULT_TEAM_ID],
            auth_enabled=True,
            permissions=make_effective_permissions(
                member,
                [DEFAULT_TEAM_ID],
                team_role="member",
            ),
        )

    app.dependency_overrides[get_conn] = override_get_conn
    app.dependency_overrides[get_auth_context] = override_auth_context

    summary = DashboardSummaryResponse(
        capabilities=DashboardCapabilities(
            reviews=True,
            resources=True,
            onboarding=True,
            analytics=True,
            usage=False,
        ),
        reviews=DashboardReviewsSection(
            total=0,
            by_status=DashboardReviewStatusCounts(),
            recent=[],
        ),
        resources=DashboardResourcesSection(
            teams=1,
            repositories=0,
            users=None,
            llm_providers=None,
        ),
        onboarding=DashboardOnboardingSection(
            steps=[
                DashboardOnboardingStep(
                    key="connect_repo",
                    label="Connect a repository",
                    done=False,
                )
            ],
            all_complete=False,
        ),
        analytics=DashboardAnalyticsSection(scope="team", team_id=DEFAULT_TEAM_ID),
    )

    with patch(
        "app.api.v1.dashboard.get_dashboard_summary",
        new=AsyncMock(return_value=summary),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/dashboard/summary")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["capabilities"]["usage"] is False
    assert data["resources"]["users"] is None
    assert data["resources"]["llm_providers"] is None
    assert data["analytics"]["scope"] == "team"


@pytest.mark.asyncio
async def test_get_dashboard_summary_service_empty_without_teams() -> None:
    from app.services.dashboard import get_dashboard_summary

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
