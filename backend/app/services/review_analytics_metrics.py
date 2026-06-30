from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from statistics import median
from uuid import UUID, uuid4

from app.repositories.repo_integrations import (
    RepoIntegrationRepository,
    RepoIntegrationRow,
)
from app.repositories.review_analytics import ReviewAnalyticsRepository
from app.repositories.reviews import ReviewRepository
from app.services.review_analytics_events import supports_review_analytics


@dataclass(frozen=True, slots=True)
class AnalyticsComputationResult:
    job_run_id: UUID
    window_start: datetime
    window_end: datetime
    rows_upserted: int


@dataclass(slots=True)
class _PrAggregate:
    repo_full_name: str
    pr_number: int
    repo_integration_id: UUID | None
    team_id: UUID | None
    opened_at: datetime | None = None
    ready_at: datetime | None = None
    merged_at: datetime | None = None
    ai_reviewed: bool = False
    earliest_ai_comment_at: datetime | None = None
    earliest_human_reply_at: datetime | None = None
    quality_feedback_values: list[str] = field(default_factory=list)
    resolution_feedback_values: list[str] = field(default_factory=list)
    actionable_finding_ids: set[str] = field(default_factory=set)
    applied_or_fixed_finding_ids: set[str] = field(default_factory=set)


async def compute_review_analytics(
    conn,
    *,
    window_days: int,
    window_end: datetime | None = None,
) -> AnalyticsComputationResult:
    end = (window_end or datetime.now(tz=UTC)).astimezone(UTC)
    start = end - timedelta(days=window_days)
    job_run_id = uuid4()

    integration_repo = RepoIntegrationRepository(conn)
    integrations = [
        row
        for row in await integration_repo.list_all()
        if row.enabled and supports_review_analytics(row.git_provider)
    ]
    rows = await _build_metric_rows(
        conn,
        integrations=integrations,
        window_start=start,
        window_end=end,
        job_run_id=job_run_id,
    )
    analytics_repo = ReviewAnalyticsRepository(conn)
    count = await analytics_repo.upsert_metric_rows(rows)
    return AnalyticsComputationResult(
        job_run_id=job_run_id,
        window_start=start,
        window_end=end,
        rows_upserted=count,
    )


async def _build_metric_rows(
    conn,
    *,
    integrations: list[RepoIntegrationRow],
    window_start: datetime,
    window_end: datetime,
    job_run_id: UUID,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not integrations:
        return rows

    repo_full_names = [row.repo_full_name for row in integrations if row.repo_full_name]
    analytics_repo = ReviewAnalyticsRepository(conn)
    review_repo = ReviewRepository(conn)
    events = await analytics_repo.list_engagement_events(
        provider="github",
        repo_full_names=repo_full_names,
        before=window_end,
    )
    reviews = await review_repo.list_reviews(
        repo_full_names=repo_full_names,
        limit=10000,
        offset=0,
    )

    integration_by_repo = {row.repo_full_name: row for row in integrations}
    prs = _aggregate_prs(events, reviews, integration_by_repo, window_start, window_end)
    all_rows = _rows_for_dimension(
        prs=list(prs.values()),
        dimension_key="all",
        provider="github",
        repo_integration_id=None,
        team_id=None,
        repo_full_name="",
        window_start=window_start,
        window_end=window_end,
        job_run_id=job_run_id,
    )
    rows.extend(all_rows)
    team_ids = sorted({row.team_id for row in integrations if row.team_id is not None})
    for team_id in team_ids:
        scoped = [value for value in prs.values() if value.team_id == team_id]
        if not scoped:
            continue
        rows.extend(
            _rows_for_dimension(
                prs=scoped,
                dimension_key=f"team:{team_id}",
                provider="github",
                repo_integration_id=None,
                team_id=team_id,
                repo_full_name="",
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            )
        )
    for repo_full_name, integration in integration_by_repo.items():
        scoped = [
            value for value in prs.values() if value.repo_full_name == repo_full_name
        ]
        rows.extend(
            _rows_for_dimension(
                prs=scoped,
                dimension_key=f"repo:{integration.id}",
                provider="github",
                repo_integration_id=integration.id,
                team_id=integration.team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            )
        )
    return rows


def _aggregate_prs(
    events,
    reviews,
    integration_by_repo: dict[str, RepoIntegrationRow],
    window_start: datetime,
    window_end: datetime,
) -> dict[tuple[str, int], _PrAggregate]:
    prs: dict[tuple[str, int], _PrAggregate] = {}
    for event in events:
        key = (event.repo_full_name, event.pr_number)
        integration = integration_by_repo.get(event.repo_full_name)
        pr = prs.get(key)
        if pr is None:
            pr = _PrAggregate(
                repo_full_name=event.repo_full_name,
                pr_number=event.pr_number,
                repo_integration_id=(
                    integration.id if integration else event.repo_integration_id
                ),
                team_id=integration.team_id if integration else event.team_id,
            )
            prs[key] = pr
        if event.event_type == "pr_opened":
            pr.opened_at = _earlier(pr.opened_at, event.event_at)
        elif event.event_type == "pr_reopened":
            pr.opened_at = _earlier(pr.opened_at, event.event_at)
        elif event.event_type == "pr_ready_for_review":
            pr.ready_at = _earlier(pr.ready_at, event.event_at)
        elif event.event_type == "pr_merged":
            pr.merged_at = _earlier(pr.merged_at, event.event_at)
        elif event.event_type == "ai_comment_posted":
            pr.earliest_ai_comment_at = _earlier(
                pr.earliest_ai_comment_at,
                event.event_at,
            )
            if event.review_finding_id is not None:
                pr.actionable_finding_ids.add(str(event.review_finding_id))
        elif event.event_type == "human_replied":
            pr.earliest_human_reply_at = _earlier(
                pr.earliest_human_reply_at,
                event.event_at,
            )
        elif event.event_type == "feedback_classified":
            feedback_group = str(event.normalized_json.get("feedback_group") or "")
            feedback_value = str(event.normalized_json.get("feedback_value") or "")
            if feedback_group == "quality_feedback" and feedback_value:
                pr.quality_feedback_values.append(feedback_value)
            if feedback_group == "resolution_feedback" and feedback_value:
                pr.resolution_feedback_values.append(feedback_value)
                if (
                    feedback_value in {"applied", "fixed"}
                    and event.review_finding_id is not None
                ):
                    pr.applied_or_fixed_finding_ids.add(str(event.review_finding_id))

    for review in reviews:
        if review.created_at > window_end:
            continue
        key = (review.repo_full_name, review.pr_number)
        integration = integration_by_repo.get(review.repo_full_name)
        pr = prs.get(key)
        if pr is None:
            pr = _PrAggregate(
                repo_full_name=review.repo_full_name,
                pr_number=review.pr_number,
                repo_integration_id=(
                    integration.id if integration else review.repo_integration_id
                ),
                team_id=integration.team_id if integration else review.team_id,
            )
            prs[key] = pr
        pr.ai_reviewed = True

    eligible_keys = [
        key
        for key, value in prs.items()
        if _is_eligible_pr(value, window_start, window_end)
    ]
    return {key: prs[key] for key in eligible_keys}


def _rows_for_dimension(
    *,
    prs: list[_PrAggregate],
    dimension_key: str,
    provider: str,
    repo_integration_id: UUID | None,
    team_id: UUID | None,
    repo_full_name: str,
    window_start: datetime,
    window_end: datetime,
    job_run_id: UUID,
) -> list[dict[str, object]]:
    metrics: list[dict[str, object]] = []
    ai_merged = [
        pr
        for pr in prs
        if pr.ai_reviewed
        and pr.merged_at
        and window_start <= pr.merged_at <= window_end
    ]
    pr_time_samples = [
        (pr.merged_at - pr.opened_at).total_seconds()
        for pr in ai_merged
        if pr.opened_at and pr.merged_at
    ]
    ready_time_samples = [
        (pr.merged_at - (pr.ready_at or pr.opened_at)).total_seconds()
        for pr in ai_merged
        if pr.merged_at and (pr.ready_at or pr.opened_at)
    ]
    first_reply_samples = [
        (pr.earliest_human_reply_at - pr.earliest_ai_comment_at).total_seconds()
        for pr in prs
        if pr.earliest_ai_comment_at
        and pr.earliest_human_reply_at
        and window_start <= pr.earliest_human_reply_at <= window_end
    ]

    quality_events = _feedback_events(prs, "quality_feedback")
    helpful_count = sum(1 for value in quality_events if value == "helpful")
    rated_count = len(quality_events)
    applied_fixed = sum(len(pr.applied_or_fixed_finding_ids) for pr in prs)
    actionable_count = sum(len(pr.actionable_finding_ids) for pr in prs)
    reviewed_prs = sum(1 for pr in prs if pr.ai_reviewed)
    eligible_prs = len(prs)

    metrics.extend(
        [
            _metric_row(
                metric_key="pr_time_to_merge",
                metric_value_num=_median_or_zero(pr_time_samples),
                sample_size=len(pr_time_samples),
                provider=provider,
                dimension_key=dimension_key,
                repo_integration_id=repo_integration_id,
                team_id=team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            ),
            _metric_row(
                metric_key="review_ready_to_merge",
                metric_value_num=_median_or_zero(ready_time_samples),
                sample_size=len(ready_time_samples),
                provider=provider,
                dimension_key=dimension_key,
                repo_integration_id=repo_integration_id,
                team_id=team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            ),
            _metric_row(
                metric_key="time_to_first_human_reply",
                metric_value_num=_median_or_zero(first_reply_samples),
                sample_size=len(first_reply_samples),
                provider=provider,
                dimension_key=dimension_key,
                repo_integration_id=repo_integration_id,
                team_id=team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            ),
            _metric_row(
                metric_key="helpful_rate",
                metric_value_num=_rate(helpful_count, rated_count),
                numerator=float(helpful_count),
                denominator=float(rated_count),
                sample_size=rated_count,
                provider=provider,
                dimension_key=dimension_key,
                repo_integration_id=repo_integration_id,
                team_id=team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            ),
            _metric_row(
                metric_key="applied_or_fixed_findings_rate",
                metric_value_num=_rate(applied_fixed, actionable_count),
                numerator=float(applied_fixed),
                denominator=float(actionable_count),
                sample_size=actionable_count,
                provider=provider,
                dimension_key=dimension_key,
                repo_integration_id=repo_integration_id,
                team_id=team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            ),
            _metric_row(
                metric_key="ai_review_coverage",
                metric_value_num=_rate(reviewed_prs, eligible_prs),
                numerator=float(reviewed_prs),
                denominator=float(eligible_prs),
                sample_size=eligible_prs,
                provider=provider,
                dimension_key=dimension_key,
                repo_integration_id=repo_integration_id,
                team_id=team_id,
                repo_full_name=repo_full_name,
                window_start=window_start,
                window_end=window_end,
                job_run_id=job_run_id,
            ),
        ]
    )
    return metrics


def _feedback_events(prs: list[_PrAggregate], feedback_group: str) -> list[str]:
    values: list[str] = []
    for pr in prs:
        if feedback_group == "quality_feedback":
            values.extend(pr.quality_feedback_values)
        elif feedback_group == "resolution_feedback":
            values.extend(pr.resolution_feedback_values)
    return values


def _metric_row(
    *,
    metric_key: str,
    metric_value_num: float,
    sample_size: int,
    provider: str,
    dimension_key: str,
    repo_integration_id: UUID | None,
    team_id: UUID | None,
    repo_full_name: str,
    window_start: datetime,
    window_end: datetime,
    job_run_id: UUID,
    numerator: float | None = None,
    denominator: float | None = None,
) -> dict[str, object]:
    return {
        "metric_key": metric_key,
        "provider": provider,
        "granularity": "rolling_window",
        "window_start": window_start,
        "window_end": window_end,
        "dimension_key": dimension_key,
        "repo_integration_id": repo_integration_id,
        "team_id": team_id,
        "repo_full_name": repo_full_name,
        "metric_value_num": metric_value_num,
        "numerator": numerator,
        "denominator": denominator,
        "sample_size": sample_size,
        "dimensions_json": {
            "dimension_key": dimension_key,
            "provider": provider,
            "repo_full_name": repo_full_name,
            "team_id": str(team_id) if team_id else None,
            "repo_integration_id": (
                str(repo_integration_id) if repo_integration_id else None
            ),
        },
        "job_run_id": job_run_id,
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _median_or_zero(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _earlier(current: datetime | None, candidate: datetime) -> datetime:
    if current is None or candidate < current:
        return candidate
    return current


def _is_eligible_pr(
    pr: _PrAggregate,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    timestamps = [value for value in [pr.opened_at, pr.ready_at, pr.merged_at] if value]
    return any(window_start <= value <= window_end for value in timestamps)
