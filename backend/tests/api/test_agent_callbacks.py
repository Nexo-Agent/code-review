import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import CodeReviewSettings
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.reviews import ReviewRow
from app.services.review_callback_auth import sign_payload


@pytest.fixture
def callback_secret() -> str:
    return "test-callback-secret"


@pytest.fixture
async def client(callback_secret: str, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    monkeypatch.setattr(
        "app.api.v1.agent_callbacks.get_code_review_settings",
        lambda: CodeReviewSettings(agent_callback_secret=callback_secret),
    )
    app = create_app()
    mock_conn = object()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _review_row(review_id: UUID | None = None) -> ReviewRow:
    now = datetime.now(tz=UTC)
    rid = review_id or UUID("550e8400-e29b-41d4-a716-446655440000")
    return ReviewRow(
        id=rid,
        provider="github",
        repo_full_name="org/repo",
        pr_number=42,
        head_sha="abc123",
        status="pending",
        delivery_id="del-1",
        repo_integration_id=UUID("11111111-1111-1111-1111-111111111111"),
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
    )


def _started_payload(review_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "event": "review.started",
        "review_id": review_id,
        "occurred_at": "2026-06-25T10:00:00Z",
        "agent": {"name": "coreview-agent", "version": "0.1.0"},
        "request": {
            "git_provider": "github",
            "repo_full_name": "org/repo",
            "pr_number": 42,
            "head_sha": "abc123",
        },
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_agent_callback_started_updates_status(
    client: AsyncClient,
    callback_secret: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_repo = AsyncMock()
    mock_repo.get.return_value = _review_row()
    mock_repo.update_status = AsyncMock()

    monkeypatch.setattr(
        "app.services.review_callback_handler.ReviewRepository",
        lambda _conn: mock_repo,
    )

    body = json.dumps(_started_payload(review_id)).encode()
    response = await client.post(
        "/api/v1/agent/review-events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Review-Signature-256": sign_payload(body, callback_secret),
        },
    )

    assert response.status_code == 204
    mock_repo.update_status.assert_awaited_once_with(
        UUID(review_id),
        status="running",
        set_started=True,
    )


@pytest.mark.asyncio
async def test_agent_callback_invalid_signature_returns_401(
    client: AsyncClient,
) -> None:
    review_id = "550e8400-e29b-41d4-a716-446655440000"
    body = json.dumps(_started_payload(review_id)).encode()
    response = await client.post(
        "/api/v1/agent/review-events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Review-Signature-256": "sha256=deadbeef",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agent_callback_unknown_review_returns_404(
    client: AsyncClient,
    callback_secret: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_repo = AsyncMock()
    mock_repo.get.return_value = None
    monkeypatch.setattr(
        "app.services.review_callback_handler.ReviewRepository",
        lambda _conn: mock_repo,
    )

    body = json.dumps(_started_payload(review_id)).encode()
    response = await client.post(
        "/api/v1/agent/review-events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Review-Signature-256": sign_payload(body, callback_secret),
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agent_callback_completed_persists_findings(
    client: AsyncClient,
    callback_secret: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_repo = AsyncMock()
    mock_repo.get.return_value = _review_row()
    mock_repo.replace_findings = AsyncMock()
    mock_repo.update_status = AsyncMock()
    monkeypatch.setattr(
        "app.services.review_callback_handler.ReviewRepository",
        lambda _conn: mock_repo,
    )

    payload = _started_payload(review_id)
    payload["event"] = "review.completed"
    payload["result"] = {
        "findings": [
            {
                "severity": "warning",
                "title": "Issue",
                "body": "Details",
                "file_path": "src/a.py",
                "line_start": 10,
                "line_end": 12,
            }
        ],
        "github": {
            "summary_comment_posted": True,
            "inline_comments_posted": 1,
            "inline_comments_skipped": 0,
        },
    }
    body = json.dumps(payload).encode()
    response = await client.post(
        "/api/v1/agent/review-events",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Review-Signature-256": sign_payload(body, callback_secret),
        },
    )

    assert response.status_code == 204
    mock_repo.replace_findings.assert_awaited_once()
    findings = mock_repo.replace_findings.await_args.args[1]
    assert findings[0]["title"] == "Issue"
    mock_repo.update_status.assert_awaited_once_with(
        UUID(review_id),
        status="completed",
        set_completed=True,
    )
