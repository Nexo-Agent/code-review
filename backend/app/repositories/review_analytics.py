from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class ReviewCommentArtifactRow:
    id: UUID
    review_id: UUID
    review_finding_id: UUID | None
    provider: str
    repo_full_name: str
    pr_number: int
    comment_kind: str
    remote_comment_id: str
    remote_thread_id: str | None
    file_path: str | None
    line_start: int | None
    side: str
    posted_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewEngagementEventRow:
    id: UUID
    provider: str
    repo_full_name: str
    pr_number: int
    review_id: UUID | None
    review_finding_id: UUID | None
    comment_artifact_id: UUID | None
    repo_integration_id: UUID | None
    team_id: UUID | None
    event_family: str
    event_type: str
    event_at: datetime
    actor_login: str
    actor_type: str
    provider_delivery_id: str
    provider_event_id: str
    provider_object_id: str
    dedup_key: str
    payload_json: dict
    normalized_json: dict
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewMetricAnalyticsRow:
    id: UUID
    metric_key: str
    provider: str
    granularity: str
    window_start: datetime
    window_end: datetime
    dimension_key: str
    repo_integration_id: UUID | None
    team_id: UUID | None
    repo_full_name: str
    metric_value_num: float
    numerator: float | None
    denominator: float | None
    sample_size: int
    dimensions_json: dict
    job_run_id: UUID
    computed_at: datetime


class ReviewAnalyticsRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def replace_comment_artifacts(
        self,
        *,
        review_id: UUID,
        provider: str,
        repo_full_name: str,
        pr_number: int,
        artifacts: list[dict[str, object]],
        finding_ids_by_index: dict[int, UUID],
    ) -> list[ReviewCommentArtifactRow]:
        rows: list[ReviewCommentArtifactRow] = []
        async with self._conn.transaction():
            await self._conn.execute(
                "DELETE FROM review_comment_artifacts WHERE review_id = $1",
                review_id,
            )
            for artifact in artifacts:
                finding_id = None
                finding_index = artifact.get("finding_index")
                if isinstance(finding_index, int):
                    finding_id = finding_ids_by_index.get(finding_index)
                row = await self._conn.fetchrow(
                    """
                    INSERT INTO review_comment_artifacts (
                        review_id, review_finding_id, provider, repo_full_name,
                        pr_number, comment_kind, remote_comment_id, remote_thread_id,
                        file_path, line_start, side, posted_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                    )
                    RETURNING id, review_id, review_finding_id, provider,
                              repo_full_name,
                              pr_number, comment_kind, remote_comment_id,
                              remote_thread_id, file_path, line_start, side,
                              posted_at, created_at
                    """,
                    review_id,
                    finding_id,
                    provider,
                    repo_full_name,
                    pr_number,
                    str(artifact["comment_kind"]),
                    str(artifact["remote_comment_id"]),
                    artifact.get("remote_thread_id"),
                    artifact.get("file_path"),
                    artifact.get("line_start"),
                    str(artifact.get("side") or "RIGHT"),
                    artifact["posted_at"],
                )
                if row is not None:
                    rows.append(_row_to_comment_artifact(row))
        return rows

    async def get_comment_artifact_by_remote_comment(
        self,
        *,
        provider: str,
        repo_full_name: str,
        pr_number: int,
        remote_comment_id: str,
    ) -> ReviewCommentArtifactRow | None:
        row = await self._conn.fetchrow(
            """
            SELECT id, review_id, review_finding_id, provider, repo_full_name,
                   pr_number, comment_kind, remote_comment_id, remote_thread_id,
                   file_path, line_start, side, posted_at, created_at
            FROM review_comment_artifacts
            WHERE provider = $1 AND repo_full_name = $2
              AND pr_number = $3 AND remote_comment_id = $4
            """,
            provider,
            repo_full_name,
            pr_number,
            remote_comment_id,
        )
        return _row_to_comment_artifact(row) if row else None

    async def insert_engagement_event(
        self,
        *,
        provider: str,
        repo_full_name: str,
        pr_number: int,
        review_id: UUID | None,
        review_finding_id: UUID | None,
        comment_artifact_id: UUID | None,
        repo_integration_id: UUID | None,
        team_id: UUID | None,
        event_family: str,
        event_type: str,
        event_at: datetime,
        actor_login: str,
        actor_type: str,
        provider_delivery_id: str,
        provider_event_id: str,
        provider_object_id: str,
        dedup_key: str,
        payload_json: dict,
        normalized_json: dict,
    ) -> ReviewEngagementEventRow | None:
        row = await self._conn.fetchrow(
            """
            INSERT INTO review_engagement_events (
                provider, repo_full_name, pr_number, review_id, review_finding_id,
                comment_artifact_id, repo_integration_id, team_id, event_family,
                event_type, event_at, actor_login, actor_type, provider_delivery_id,
                provider_event_id, provider_object_id, dedup_key, payload_json,
                normalized_json
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18::jsonb, $19::jsonb
            )
            ON CONFLICT (dedup_key) DO NOTHING
            RETURNING id, provider, repo_full_name, pr_number, review_id,
                      review_finding_id, comment_artifact_id, repo_integration_id,
                      team_id, event_family, event_type, event_at, actor_login,
                      actor_type, provider_delivery_id, provider_event_id,
                      provider_object_id, dedup_key, payload_json, normalized_json,
                      created_at
            """,
            provider,
            repo_full_name,
            pr_number,
            review_id,
            review_finding_id,
            comment_artifact_id,
            repo_integration_id,
            team_id,
            event_family,
            event_type,
            event_at,
            actor_login,
            actor_type,
            provider_delivery_id,
            provider_event_id,
            provider_object_id,
            dedup_key,
            _encode_json(payload_json),
            _encode_json(normalized_json),
        )
        return _row_to_engagement_event(row) if row else None

    async def list_engagement_events(
        self,
        *,
        provider: str,
        repo_full_names: list[str],
        before: datetime,
    ) -> list[ReviewEngagementEventRow]:
        if not repo_full_names:
            return []
        rows = await self._conn.fetch(
            """
            SELECT id, provider, repo_full_name, pr_number, review_id,
                   review_finding_id, comment_artifact_id, repo_integration_id,
                   team_id, event_family, event_type, event_at, actor_login,
                   actor_type, provider_delivery_id, provider_event_id,
                   provider_object_id, dedup_key, payload_json, normalized_json,
                   created_at
            FROM review_engagement_events
            WHERE provider = $1
              AND repo_full_name = ANY($2::text[])
              AND event_at <= $3
            ORDER BY event_at ASC, created_at ASC
            """,
            provider,
            repo_full_names,
            before,
        )
        return [_row_to_engagement_event(row) for row in rows]

    async def upsert_metric_rows(
        self,
        rows: list[dict[str, object]],
    ) -> int:
        if not rows:
            return 0
        async with self._conn.transaction():
            for row in rows:
                await self._conn.execute(
                    """
                    INSERT INTO review_metrics_analytics (
                        metric_key, provider, granularity, window_start, window_end,
                        dimension_key, repo_integration_id, team_id, repo_full_name,
                        metric_value_num, numerator, denominator, sample_size,
                        dimensions_json, job_run_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                        $14::jsonb, $15
                    )
                    ON CONFLICT (
                        metric_key, provider, granularity, window_start, window_end,
                        dimension_key
                    ) DO UPDATE
                    SET repo_integration_id = EXCLUDED.repo_integration_id,
                        team_id = EXCLUDED.team_id,
                        repo_full_name = EXCLUDED.repo_full_name,
                        metric_value_num = EXCLUDED.metric_value_num,
                        numerator = EXCLUDED.numerator,
                        denominator = EXCLUDED.denominator,
                        sample_size = EXCLUDED.sample_size,
                        dimensions_json = EXCLUDED.dimensions_json,
                        job_run_id = EXCLUDED.job_run_id,
                        computed_at = now()
                    """,
                    row["metric_key"],
                    row["provider"],
                    row["granularity"],
                    row["window_start"],
                    row["window_end"],
                    row["dimension_key"],
                    row.get("repo_integration_id"),
                    row.get("team_id"),
                    row.get("repo_full_name") or "",
                    row["metric_value_num"],
                    row.get("numerator"),
                    row.get("denominator"),
                    row["sample_size"],
                    _encode_json(row["dimensions_json"]),
                    row["job_run_id"],
                )
        return len(rows)

    async def list_latest_metric_rows(
        self,
        *,
        provider: str,
        granularity: str = "rolling_window",
    ) -> list[ReviewMetricAnalyticsRow]:
        job_run_id = await self._conn.fetchval(
            """
            SELECT job_run_id
            FROM review_metrics_analytics
            WHERE provider = $1 AND granularity = $2
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            provider,
            granularity,
        )
        if job_run_id is None:
            return []
        rows = await self._conn.fetch(
            """
            SELECT id, metric_key, provider, granularity, window_start, window_end,
                   dimension_key, repo_integration_id, team_id, repo_full_name,
                   metric_value_num, numerator, denominator, sample_size,
                   dimensions_json, job_run_id, computed_at
            FROM review_metrics_analytics
            WHERE job_run_id = $1
            ORDER BY repo_full_name ASC, metric_key ASC
            """,
            job_run_id,
        )
        return [_row_to_metric_analytics(row) for row in rows]

    async def list_metric_history(
        self,
        *,
        provider: str,
        metric_key: str,
        dimension_key: str,
        start: datetime,
        end: datetime,
        granularity: str = "rolling_window",
    ) -> list[ReviewMetricAnalyticsRow]:
        rows = await self._conn.fetch(
            """
            SELECT id, metric_key, provider, granularity, window_start, window_end,
                   dimension_key, repo_integration_id, team_id, repo_full_name,
                   metric_value_num, numerator, denominator, sample_size,
                   dimensions_json, job_run_id, computed_at
            FROM review_metrics_analytics
            WHERE provider = $1
              AND metric_key = $2
              AND dimension_key = $3
              AND granularity = $4
              AND computed_at >= $5
              AND computed_at <= $6
            ORDER BY computed_at ASC
            """,
            provider,
            metric_key,
            dimension_key,
            granularity,
            start,
            end,
        )
        return [_row_to_metric_analytics(row) for row in rows]


def _encode_json(value: dict) -> str:
    import json

    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _decode_json(value: object) -> dict:
    import json

    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _row_to_comment_artifact(row: asyncpg.Record) -> ReviewCommentArtifactRow:
    return ReviewCommentArtifactRow(
        id=row["id"],
        review_id=row["review_id"],
        review_finding_id=row["review_finding_id"],
        provider=row["provider"],
        repo_full_name=row["repo_full_name"],
        pr_number=row["pr_number"],
        comment_kind=row["comment_kind"],
        remote_comment_id=row["remote_comment_id"],
        remote_thread_id=row["remote_thread_id"],
        file_path=row["file_path"],
        line_start=row["line_start"],
        side=row["side"],
        posted_at=row["posted_at"],
        created_at=row["created_at"],
    )


def _row_to_engagement_event(row: asyncpg.Record) -> ReviewEngagementEventRow:
    return ReviewEngagementEventRow(
        id=row["id"],
        provider=row["provider"],
        repo_full_name=row["repo_full_name"],
        pr_number=row["pr_number"],
        review_id=row["review_id"],
        review_finding_id=row["review_finding_id"],
        comment_artifact_id=row["comment_artifact_id"],
        repo_integration_id=row["repo_integration_id"],
        team_id=row["team_id"],
        event_family=row["event_family"],
        event_type=row["event_type"],
        event_at=row["event_at"],
        actor_login=row["actor_login"],
        actor_type=row["actor_type"],
        provider_delivery_id=row["provider_delivery_id"],
        provider_event_id=row["provider_event_id"],
        provider_object_id=row["provider_object_id"],
        dedup_key=row["dedup_key"],
        payload_json=_decode_json(row["payload_json"]),
        normalized_json=_decode_json(row["normalized_json"]),
        created_at=row["created_at"],
    )


def _row_to_metric_analytics(row: asyncpg.Record) -> ReviewMetricAnalyticsRow:
    return ReviewMetricAnalyticsRow(
        id=row["id"],
        metric_key=row["metric_key"],
        provider=row["provider"],
        granularity=row["granularity"],
        window_start=row["window_start"],
        window_end=row["window_end"],
        dimension_key=row["dimension_key"],
        repo_integration_id=row["repo_integration_id"],
        team_id=row["team_id"],
        repo_full_name=row["repo_full_name"],
        metric_value_num=row["metric_value_num"],
        numerator=row["numerator"],
        denominator=row["denominator"],
        sample_size=row["sample_size"],
        dimensions_json=_decode_json(row["dimensions_json"]),
        job_run_id=row["job_run_id"],
        computed_at=row["computed_at"],
    )
