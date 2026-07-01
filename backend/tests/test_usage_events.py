from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from coreview_shared.schemas.review_callback import (
    ReviewCallbackAgent,
    ReviewCallbackEvent,
    ReviewCallbackLlmCallUsage,
    ReviewCallbackRequest,
    ReviewCallbackTokenUsage,
)

from app.repositories.teams import DEFAULT_TEAM_ID
from app.services.review_callback_handler import handle_review_callback
from tests.conftest import make_review_row


@pytest.mark.asyncio
async def test_review_callback_persists_token_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    review_row = make_review_row(id=review_id, team_id=DEFAULT_TEAM_ID)

    mock_repo = AsyncMock()
    mock_repo.get.return_value = review_row
    mock_repo.update_request_metadata = AsyncMock()
    mock_repo.update_status = AsyncMock()
    mock_repo.replace_findings = AsyncMock(return_value=[])
    mock_repo.update_delivery_stats = AsyncMock()

    mock_usage_repo = AsyncMock()
    mock_usage_repo.insert_llm_calls.return_value = 2

    mock_integration_repo = AsyncMock()
    mock_integration_repo.get.return_value = SimpleNamespace(
        git_provider="github",
        llm_provider_id=None,
        team_id=DEFAULT_TEAM_ID,
    )

    mock_llm_provider = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        model="gpt-4o",
        provider_id="openai-compat",
        enabled=True,
        organization_id=UUID("33333333-3333-3333-3333-333333333333"),
    )

    monkeypatch.setattr(
        "app.services.review_callback_handler.ReviewRepository",
        lambda _conn: mock_repo,
    )
    monkeypatch.setattr(
        "app.services.review_callback_handler.RepoIntegrationRepository",
        lambda _conn: mock_integration_repo,
    )
    monkeypatch.setattr(
        "app.services.usage_events.UsageRepository",
        lambda _conn: mock_usage_repo,
    )
    monkeypatch.setattr(
        "app.services.usage_events.RepoIntegrationRepository",
        lambda _conn: mock_integration_repo,
    )
    monkeypatch.setattr(
        "app.services.usage_events.resolve_llm_provider_for_repo",
        AsyncMock(return_value=mock_llm_provider),
    )

    event = ReviewCallbackEvent(
        event="review.completed",
        review_id=str(review_id),
        occurred_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
        agent=ReviewCallbackAgent(name="cogito-review-agent", version="0.1.0"),
        request=ReviewCallbackRequest(
            git_provider="github",
            repo_full_name="org/repo",
            pr_number=42,
            head_sha="abc123",
        ),
        token_usage=ReviewCallbackTokenUsage(
            llm_provider_id="openai-compat",
            model="openai-compat/gpt-4o",
            calls=[
                ReviewCallbackLlmCallUsage(
                    call_index=0,
                    input_tokens=100,
                    output_tokens=20,
                    total_tokens=120,
                ),
                ReviewCallbackLlmCallUsage(
                    call_index=1,
                    input_tokens=50,
                    output_tokens=10,
                    total_tokens=60,
                ),
            ],
        ),
    )

    await handle_review_callback(object(), event)

    mock_usage_repo.insert_llm_calls.assert_awaited_once()
    kwargs = mock_usage_repo.insert_llm_calls.await_args.kwargs
    assert kwargs["review_id"] == review_id
    assert kwargs["git_provider"] == "github"
    assert len(kwargs["calls"]) == 2
