from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.repositories.review_analytics import ReviewEngagementEventRow
from app.services.review_analytics_metrics import compute_review_analytics
from tests.api.test_reviews import _llm_row, _repo_row
from tests.conftest import make_review_row


@pytest.mark.asyncio
async def test_compute_review_analytics_rolls_up_six_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = _llm_row()
    repo = _repo_row(llm)
    window_end = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)
    mock_integrations = AsyncMock(return_value=[repo])
    captured_rows: list[dict[str, object]] = []

    analytics_repo = AsyncMock()
    analytics_repo.list_engagement_events = AsyncMock(
        return_value=[
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=None,
                review_finding_id=None,
                comment_artifact_id=None,
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="pr_lifecycle",
                event_type="pr_opened",
                event_at=datetime(2026, 6, 29, 10, 0, tzinfo=UTC),
                actor_login="alice",
                actor_type="human",
                provider_delivery_id="d1",
                provider_event_id="opened",
                provider_object_id="42",
                dedup_key="1",
                payload_json={},
                normalized_json={},
                created_at=window_end,
            ),
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=None,
                review_finding_id=None,
                comment_artifact_id=None,
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="pr_lifecycle",
                event_type="pr_ready_for_review",
                event_at=datetime(2026, 6, 29, 11, 0, tzinfo=UTC),
                actor_login="alice",
                actor_type="human",
                provider_delivery_id="d2",
                provider_event_id="ready_for_review",
                provider_object_id="42",
                dedup_key="2",
                payload_json={},
                normalized_json={},
                created_at=window_end,
            ),
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=uuid4(),
                review_finding_id=uuid4(),
                comment_artifact_id=uuid4(),
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="ai_comment",
                event_type="ai_comment_posted",
                event_at=datetime(2026, 6, 29, 11, 30, tzinfo=UTC),
                actor_login="cogito-review",
                actor_type="system",
                provider_delivery_id="d3",
                provider_event_id="agent_callback",
                provider_object_id="1001",
                dedup_key="3",
                payload_json={},
                normalized_json={},
                created_at=window_end,
            ),
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=uuid4(),
                review_finding_id=uuid4(),
                comment_artifact_id=uuid4(),
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="human_reply",
                event_type="human_replied",
                event_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
                actor_login="bob",
                actor_type="human",
                provider_delivery_id="d4",
                provider_event_id="created",
                provider_object_id="1002",
                dedup_key="4",
                payload_json={},
                normalized_json={},
                created_at=window_end,
            ),
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=uuid4(),
                review_finding_id=uuid4(),
                comment_artifact_id=uuid4(),
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="feedback_classified",
                event_type="feedback_classified",
                event_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
                actor_login="bob",
                actor_type="human",
                provider_delivery_id="d5",
                provider_event_id="created",
                provider_object_id="1002",
                dedup_key="5",
                payload_json={},
                normalized_json={
                    "feedback_group": "quality_feedback",
                    "feedback_value": "helpful",
                },
                created_at=window_end,
            ),
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=uuid4(),
                review_finding_id=uuid4(),
                comment_artifact_id=uuid4(),
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="feedback_classified",
                event_type="feedback_classified",
                event_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
                actor_login="bob",
                actor_type="human",
                provider_delivery_id="d6",
                provider_event_id="created",
                provider_object_id="1003",
                dedup_key="6",
                payload_json={},
                normalized_json={
                    "feedback_group": "resolution_feedback",
                    "feedback_value": "fixed",
                },
                created_at=window_end,
            ),
            ReviewEngagementEventRow(
                id=uuid4(),
                provider="github",
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                review_id=None,
                review_finding_id=None,
                comment_artifact_id=None,
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                event_family="pr_lifecycle",
                event_type="pr_merged",
                event_at=datetime(2026, 6, 30, 8, 0, tzinfo=UTC),
                actor_login="alice",
                actor_type="human",
                provider_delivery_id="d7",
                provider_event_id="closed",
                provider_object_id="42",
                dedup_key="7",
                payload_json={},
                normalized_json={},
                created_at=window_end,
            ),
        ]
    )
    analytics_repo.upsert_metric_rows = AsyncMock(
        side_effect=lambda rows: captured_rows.extend(rows) or len(rows)
    )
    reviews_repo = AsyncMock()
    reviews_repo.list_reviews = AsyncMock(
        return_value=[
            make_review_row(
                repo_full_name=repo.repo_full_name,
                pr_number=42,
                repo_integration_id=repo.id,
                team_id=repo.team_id,
                created_at=datetime(2026, 6, 29, 11, 0, tzinfo=UTC),
            )
        ]
    )

    monkeypatch.setattr(
        "app.services.review_analytics_metrics.RepoIntegrationRepository",
        lambda _conn: AsyncMock(list_all=mock_integrations),
    )
    monkeypatch.setattr(
        "app.services.review_analytics_metrics.ReviewAnalyticsRepository",
        lambda _conn: analytics_repo,
    )
    monkeypatch.setattr(
        "app.services.review_analytics_metrics.ReviewRepository",
        lambda _conn: reviews_repo,
    )

    result = await compute_review_analytics(
        object(),
        window_days=30,
        window_end=window_end,
    )

    assert result.rows_upserted == 18
    assert len(captured_rows) == 18
    assert {row["metric_key"] for row in captured_rows} == {
        "pr_time_to_merge",
        "review_ready_to_merge",
        "time_to_first_human_reply",
        "helpful_rate",
        "applied_or_fixed_findings_rate",
        "ai_review_coverage",
    }
    assert {row["dimension_key"] for row in captured_rows} == {
        "all",
        f"team:{repo.team_id}",
        f"repo:{repo.id}",
    }
