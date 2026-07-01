from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.repositories.usage import UsageRepository

USAGE_METRIC_KEYS = (
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "llm_call_count",
    "review_count",
)


@dataclass(frozen=True, slots=True)
class UsageComputationResult:
    job_run_id: UUID
    window_start: datetime
    window_end: datetime
    rows_upserted: int


async def compute_usage_metrics(
    conn,
    *,
    window_days: int,
    window_end: datetime | None = None,
) -> UsageComputationResult:
    end = (window_end or datetime.now(tz=UTC)).astimezone(UTC)
    start = end - timedelta(days=window_days)
    job_run_id = uuid4()

    usage_repo = UsageRepository(conn)
    events = await usage_repo.list_usage_events_between(
        window_start=start,
        window_end=end,
    )

    buckets: dict[tuple[str, datetime, str], dict[str, object]] = {}
    review_ids_by_bucket: dict[tuple[str, datetime, str], set[UUID]] = defaultdict(set)

    for event in events:
        day_start = event.occurred_at.astimezone(UTC).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
        dimensions = [
            ("all", None, None, None, ""),
            (f"team:{event.team_id}", event.team_id, None, None, ""),
            (
                f"repo:{event.repo_integration_id}",
                event.team_id,
                event.repo_integration_id,
                event.llm_provider_id,
                event.git_provider,
            ),
            (
                f"llm_provider:{event.llm_provider_id}",
                event.team_id,
                event.repo_integration_id,
                event.llm_provider_id,
                event.git_provider,
            ),
            (
                f"git_provider:{event.git_provider}",
                event.team_id,
                event.repo_integration_id,
                event.llm_provider_id,
                event.git_provider,
            ),
        ]
        for dimension_key, team_id, repo_id, llm_id, git_provider in dimensions:
            if dimension_key.startswith("team:") and event.team_id is None:
                continue
            if dimension_key.startswith("repo:") and event.repo_integration_id is None:
                continue
            if (
                dimension_key.startswith("llm_provider:")
                and event.llm_provider_id is None
            ):
                continue
            if dimension_key.startswith("git_provider:") and not event.git_provider:
                continue

            for metric_key in USAGE_METRIC_KEYS:
                bucket_key = (metric_key, day_start, dimension_key)
                bucket = buckets.setdefault(
                    bucket_key,
                    {
                        "metric_key": metric_key,
                        "granularity": "day",
                        "window_start": day_start,
                        "window_end": day_end,
                        "dimension_key": dimension_key,
                        "team_id": team_id,
                        "repo_integration_id": repo_id,
                        "llm_provider_id": llm_id,
                        "git_provider": git_provider,
                        "metric_value_num": 0.0,
                        "sample_size": 0,
                        "job_run_id": job_run_id,
                    },
                )
                if metric_key == "total_tokens":
                    current = float(bucket["metric_value_num"])
                    bucket["metric_value_num"] = current + float(event.total_tokens)
                elif metric_key == "input_tokens":
                    current = float(bucket["metric_value_num"])
                    bucket["metric_value_num"] = current + float(event.input_tokens)
                elif metric_key == "output_tokens":
                    current = float(bucket["metric_value_num"])
                    bucket["metric_value_num"] = current + float(event.output_tokens)
                elif metric_key == "llm_call_count":
                    bucket["metric_value_num"] = float(bucket["metric_value_num"]) + 1.0
                elif metric_key == "review_count":
                    review_ids_by_bucket[bucket_key].add(event.review_id)

    for bucket_key, review_ids in review_ids_by_bucket.items():
        if bucket_key in buckets:
            buckets[bucket_key]["metric_value_num"] = float(len(review_ids))
            buckets[bucket_key]["sample_size"] = len(review_ids)

    for bucket_key, bucket in buckets.items():
        metric_key = bucket_key[0]
        if metric_key != "review_count":
            bucket["sample_size"] = int(bucket["metric_value_num"])

    count = await usage_repo.upsert_daily_metrics(list(buckets.values()))
    return UsageComputationResult(
        job_run_id=job_run_id,
        window_start=start,
        window_end=end,
        rows_upserted=count,
    )
