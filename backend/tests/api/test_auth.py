from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.teams import DEFAULT_TEAM_ID
from tests.conftest import make_dev_user, make_review_row


@pytest.fixture
async def app_client():
    app = create_app()
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, client
    app.dependency_overrides.clear()


def _set_auth(
    app,
    *,
    user,
    accessible_team_ids: list,
    auth_enabled: bool = True,
) -> None:
    async def override_auth_context():
        return AuthContext(
            user=user,
            accessible_team_ids=accessible_team_ids,
            auth_enabled=auth_enabled,
        )

    app.dependency_overrides[get_auth_context] = override_auth_context


@pytest.mark.asyncio
async def test_get_me_returns_user_and_team_ids(app_client) -> None:
    app, client = app_client
    dev_user = make_dev_user()
    _set_auth(
        app,
        user=dev_user,
        accessible_team_ids=[DEFAULT_TEAM_ID],
        auth_enabled=False,
    )

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == dev_user.email
    assert data["team_ids"] == [str(DEFAULT_TEAM_ID)]
    assert data["auth_enabled"] is False


@pytest.mark.asyncio
async def test_get_review_denied_for_non_member(app_client) -> None:
    app, client = app_client
    other_team_id = uuid4()
    review = make_review_row(team_id=other_team_id)
    member = make_dev_user(is_org_admin=False)

    _set_auth(
        app,
        user=member,
        accessible_team_ids=[DEFAULT_TEAM_ID],
    )

    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=review)
    mock_member_repo = AsyncMock()
    mock_member_repo.is_member = AsyncMock(return_value=False)

    with patch("app.api.v1.reviews.ReviewRepository", return_value=mock_repo):
        with patch(
            "app.services.access_control.TeamMemberRepository",
            return_value=mock_member_repo,
        ):
            response = await client.get(f"/api/v1/reviews/{review.id}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_review_allowed_for_org_admin(app_client) -> None:
    app, client = app_client
    other_team_id = uuid4()
    review = make_review_row(team_id=other_team_id)
    admin = make_dev_user(is_org_admin=True)

    _set_auth(
        app,
        user=admin,
        accessible_team_ids=[DEFAULT_TEAM_ID, other_team_id],
    )

    mock_repo = AsyncMock()
    mock_repo.get = AsyncMock(return_value=review)
    mock_repo.list_findings = AsyncMock(return_value=[])

    with patch("app.api.v1.reviews.ReviewRepository", return_value=mock_repo):
        response = await client.get(f"/api/v1/reviews/{review.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(review.id)


@pytest.mark.asyncio
async def test_list_reviews_empty_when_user_has_no_teams(app_client) -> None:
    app, client = app_client
    member = make_dev_user(is_org_admin=False)

    _set_auth(
        app,
        user=member,
        accessible_team_ids=[],
    )

    response = await client.get("/api/v1/reviews")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}
