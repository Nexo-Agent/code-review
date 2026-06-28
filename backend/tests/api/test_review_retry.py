from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from coreview_shared.protocols import PRMetadata
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.reviews import ReviewRow
from app.repositories.teams import DEFAULT_TEAM_ID
from app.services.review_rereview import (
    ReviewInProgressError,
    ReviewNotFoundError,
    prepare_rereview,
    resolve_latest_pr_metadata,
)
from tests.conftest import make_dev_user, make_review_row


def _review_row(
    *,
    status: str = "completed",
    head_sha: str = "abc123" * 5 + "ab",
) -> ReviewRow:
    return make_review_row(
        repo_full_name="owner/repo",
        head_sha=head_sha,
        status=status,
        delivery_id=None,
        repo_integration_id=uuid4(),
        completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


def _pr_metadata(
    *,
    head_sha: str = "abc123" * 5 + "ab",
    title: str = "Fix bug",
) -> PRMetadata:
    return PRMetadata(
        repo_full_name="owner/repo",
        pr_number=42,
        title=title,
        author="dev",
        head_sha=head_sha,
        base_sha="base" * 10,
        head_ref="feature",
        base_ref="main",
        html_url="https://github.com/owner/repo/pull/42",
    )


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
async def test_retry_review_same_head_sha(client: AsyncClient) -> None:
    review = _review_row(status="completed")
    reset_review = make_review_row(
        id=review.id,
        provider=review.provider,
        repo_full_name=review.repo_full_name,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_url=review.pr_url,
        pr_author=review.pr_author,
        head_sha=review.head_sha,
        base_sha=review.base_sha,
        base_ref=review.base_ref,
        head_ref=review.head_ref,
        status="pending",
        delivery_id=review.delivery_id,
        repo_integration_id=review.repo_integration_id,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=review.created_at,
    )

    with (
        patch(
            "app.api.v1.reviews.prepare_rereview",
            AsyncMock(return_value=reset_review),
        ) as mock_prepare,
        patch("app.api.v1.reviews.run_review") as mock_task,
    ):
        mock_task.delay = MagicMock()
        response = await client.post(f"/api/v1/reviews/{review.id}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(review.id)
    assert data["status"] == "pending"
    mock_prepare.assert_awaited_once()
    mock_task.delay.assert_called_once_with(str(review.id))


@pytest.mark.asyncio
async def test_retry_review_new_head_sha(client: AsyncClient) -> None:
    review = _review_row(status="completed")
    new_sha = "def456" * 5 + "de"
    new_review = _review_row(status="pending", head_sha=new_sha)

    with (
        patch(
            "app.api.v1.reviews.prepare_rereview",
            AsyncMock(return_value=new_review),
        ),
        patch("app.api.v1.reviews.run_review") as mock_task,
    ):
        mock_task.delay = MagicMock()
        response = await client.post(f"/api/v1/reviews/{review.id}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(new_review.id)
    assert data["head_sha"] == new_sha
    mock_task.delay.assert_called_once_with(str(new_review.id))


@pytest.mark.asyncio
async def test_retry_review_not_found(client: AsyncClient) -> None:
    review_id = uuid4()
    with patch(
        "app.api.v1.reviews.prepare_rereview",
        AsyncMock(side_effect=ReviewNotFoundError(review_id)),
    ):
        response = await client.post(f"/api/v1/reviews/{review_id}/retry")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_review_in_progress(client: AsyncClient) -> None:
    review_id = uuid4()
    with patch(
        "app.api.v1.reviews.prepare_rereview",
        AsyncMock(side_effect=ReviewInProgressError("Review is already in progress")),
    ):
        response = await client.post(f"/api/v1/reviews/{review_id}/retry")

    assert response.status_code == 409
    assert response.json()["detail"] == "Review is already in progress"


@pytest.mark.asyncio
async def test_resolve_latest_pr_metadata_uses_repo_git_provider() -> None:
    review = make_review_row(
        provider="gitlab",
        repo_full_name="group/repo",
        repo_integration_id=uuid4(),
    )
    metadata = _pr_metadata(head_sha=review.head_sha)

    mock_git = MagicMock()
    mock_git.get_pr_metadata = AsyncMock(return_value=metadata)
    mock_providers = MagicMock(git=mock_git)

    conn = AsyncMock()
    with patch(
        "app.services.review_rereview.build_providers_for_repo",
        AsyncMock(return_value=mock_providers),
    ) as build_providers:
        result = await resolve_latest_pr_metadata(conn, review)

    assert result == metadata
    build_providers.assert_awaited_once_with(
        conn,
        "group/repo",
        repo_integration_id=review.repo_integration_id,
    )
    mock_git.get_pr_metadata.assert_awaited_once_with("group/repo", review.pr_number)


@pytest.mark.asyncio
async def test_prepare_rereview_resets_same_commit() -> None:
    review = _review_row(status="failed")
    reset_review = make_review_row(
        id=review.id,
        provider=review.provider,
        repo_full_name=review.repo_full_name,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_url=review.pr_url,
        pr_author=review.pr_author,
        head_sha=review.head_sha,
        base_sha=review.base_sha,
        base_ref=review.base_ref,
        head_ref=review.head_ref,
        status="pending",
        delivery_id=review.delivery_id,
        repo_integration_id=review.repo_integration_id,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=review.created_at,
    )

    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=review)
    mock_repo.reset_for_retry = AsyncMock(return_value=reset_review)
    mock_repo.create = AsyncMock()

    conn = AsyncMock()
    with (
        patch(
            "app.services.review_rereview.ReviewRepository",
            return_value=mock_repo,
        ),
        patch(
            "app.services.review_rereview.resolve_latest_pr_metadata",
            AsyncMock(return_value=_pr_metadata(head_sha=review.head_sha)),
        ),
    ):
        result = await prepare_rereview(conn, review.id)

    assert result.id == review.id
    assert result.status == "pending"
    mock_repo.reset_for_retry.assert_awaited_once_with(review.id)
    mock_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_rereview_creates_new_review_for_new_commit() -> None:
    review = _review_row(status="completed")
    new_sha = "fedcba" * 5 + "fe"
    new_review = _review_row(status="pending", head_sha=new_sha)

    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=review)
    mock_repo.create = AsyncMock(return_value=new_review)
    mock_repo.reset_for_retry = AsyncMock()

    conn = AsyncMock()
    metadata = _pr_metadata(head_sha=new_sha)
    with (
        patch(
            "app.services.review_rereview.ReviewRepository",
            return_value=mock_repo,
        ),
        patch(
            "app.services.review_rereview.resolve_latest_pr_metadata",
            AsyncMock(return_value=metadata),
        ),
    ):
        result = await prepare_rereview(conn, review.id)

    assert result.id == new_review.id
    assert result.head_sha == new_sha
    mock_repo.create.assert_awaited_once()
    create_kwargs = mock_repo.create.await_args.kwargs
    assert create_kwargs["pr_url"] == metadata.html_url
    assert create_kwargs["pr_author"] == metadata.author
    assert create_kwargs["base_sha"] == metadata.base_sha
    mock_repo.reset_for_retry.assert_not_awaited()
