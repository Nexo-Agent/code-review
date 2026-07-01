from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.repositories.usage import LlmTokenUsageRow
from app.services.usage_metrics import compute_usage_metrics


@pytest.mark.asyncio
async def test_compute_usage_metrics_rolls_up_daily_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    review_id = uuid4()
    team_id = UUID("11111111-1111-1111-1111-111111111111")
    repo_id = UUID("22222222-2222-2222-2222-222222222222")
    llm_id = UUID("33333333-3333-3333-3333-333333333333")

    events = [
        LlmTokenUsageRow(
            id=uuid4(),
            review_id=review_id,
            team_id=team_id,
            repo_integration_id=repo_id,
            llm_provider_id=llm_id,
            git_provider="github",
            model="gpt-4o",
            call_index=0,
            input_tokens=100,
            output_tokens=20,
            total_tokens=120,
            reason="tool-calls",
            occurred_at=now,
            created_at=now,
        ),
        LlmTokenUsageRow(
            id=uuid4(),
            review_id=review_id,
            team_id=team_id,
            repo_integration_id=repo_id,
            llm_provider_id=llm_id,
            git_provider="github",
            model="gpt-4o",
            call_index=1,
            input_tokens=50,
            output_tokens=10,
            total_tokens=60,
            reason="stop",
            occurred_at=now,
            created_at=now,
        ),
    ]

    mock_repo = AsyncMock()
    mock_repo.list_usage_events_between.return_value = events
    mock_repo.upsert_daily_metrics.return_value = 10

    monkeypatch.setattr(
        "app.services.usage_metrics.UsageRepository",
        lambda _conn: mock_repo,
    )

    result = await compute_usage_metrics(object(), window_days=7, window_end=now)

    assert result.rows_upserted == 10
    mock_repo.upsert_daily_metrics.assert_awaited_once()
    rows = mock_repo.upsert_daily_metrics.await_args.args[0]
    all_total = next(
        row
        for row in rows
        if row["metric_key"] == "total_tokens" and row["dimension_key"] == "all"
    )
    assert all_total["metric_value_num"] == 180.0
