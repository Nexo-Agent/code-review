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


@pytest.mark.asyncio
async def test_list_reviews_filters_by_pr_number(client: AsyncClient) -> None:
    review = make_review_row(
        id=uuid4(),
        repo_full_name="owner/repo",
        pr_number=42,
        head_sha="abc123" * 5 + "ab",
    )
    mock_repo = AsyncMock()
    mock_repo.list_reviews = AsyncMock(return_value=[review])
    mock_repo.count_reviews = AsyncMock(return_value=1)

    with patch("app.api.v1.reviews.ReviewRepository", return_value=mock_repo):
        response = await client.get("/api/v1/reviews?repo=owner/repo&pr=42")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["pr_number"] == 42
    mock_repo.list_reviews.assert_awaited_once_with(
        team_ids=[DEFAULT_TEAM_ID],
        status=None,
        repo_full_name="owner/repo",
        pr_number=42,
        limit=50,
        offset=0,
    )
