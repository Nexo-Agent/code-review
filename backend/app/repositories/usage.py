from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg


@dataclass(frozen=True, slots=True)
class LlmTokenUsageRow:
    id: UUID
    review_id: UUID
    team_id: UUID | None
    repo_integration_id: UUID | None
    llm_provider_id: UUID | None
    git_provider: str
    model: str
    call_index: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    reason: str
    occurred_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UsageMetricDailyRow:
    id: UUID
    metric_key: str
    granularity: str
    window_start: datetime
    window_end: datetime
    dimension_key: str
    team_id: UUID | None
    repo_integration_id: UUID | None
    llm_provider_id: UUID | None
    git_provider: str
    metric_value_num: float
    sample_size: int
    job_run_id: UUID
    computed_at: datetime


@dataclass(frozen=True, slots=True)
class UsageSummary:
    total_tokens: int
    input_tokens: int
    output_tokens: int
    llm_call_count: int
    review_count: int


@dataclass(frozen=True, slots=True)
class UsageHistoryPoint:
    window_start: datetime
    window_end: datetime
    metric_value_num: float
    sample_size: int


@dataclass(frozen=True, slots=True)
class UsageBreakdownRow:
    dimension_id: str
    dimension_label: str
    review_count: int
    llm_call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    percent_of_total: float


@dataclass(frozen=True, slots=True)
class UsageFilters:
    team_id: UUID | None = None
    repo_integration_id: UUID | None = None
    git_provider: str | None = None
    llm_provider_id: UUID | None = None
    start: datetime | None = None
    end: datetime | None = None


class UsageRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def insert_llm_calls(
        self,
        *,
        review_id: UUID,
        team_id: UUID | None,
        repo_integration_id: UUID | None,
        llm_provider_id: UUID | None,
        git_provider: str,
        model: str,
        occurred_at: datetime,
        calls: list[dict[str, object]],
    ) -> int:
        if not calls:
            return 0
        inserted = 0
        for call in calls:
            call_index = int(call["call_index"])
            exists = await self._conn.fetchval(
                """
                SELECT 1 FROM llm_token_usage
                WHERE review_id = $1 AND call_index = $2
                """,
                review_id,
                call_index,
            )
            if exists:
                continue
            await self._conn.execute(
                """
                INSERT INTO llm_token_usage (
                    review_id, team_id, repo_integration_id, llm_provider_id,
                    git_provider, model, call_index, input_tokens, output_tokens,
                    total_tokens, reason, occurred_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                )
                """,
                review_id,
                team_id,
                repo_integration_id,
                llm_provider_id,
                git_provider,
                model,
                call_index,
                int(call["input_tokens"]),
                int(call["output_tokens"]),
                int(call["total_tokens"]),
                str(call.get("reason", "")),
                occurred_at,
            )
            inserted += 1
        return inserted

    async def query_summary(self, filters: UsageFilters) -> UsageSummary:
        where_sql, args = _build_where_clause(filters, start_index=1)
        row = await self._conn.fetchrow(
            f"""
            SELECT
                COALESCE(SUM(total_tokens), 0)::bigint AS total_tokens,
                COALESCE(SUM(input_tokens), 0)::bigint AS input_tokens,
                COALESCE(SUM(output_tokens), 0)::bigint AS output_tokens,
                COUNT(*)::int AS llm_call_count,
                COUNT(DISTINCT review_id)::int AS review_count
            FROM llm_token_usage
            WHERE {where_sql}
            """,
            *args,
        )
        assert row is not None
        return UsageSummary(
            total_tokens=int(row["total_tokens"]),
            input_tokens=int(row["input_tokens"]),
            output_tokens=int(row["output_tokens"]),
            llm_call_count=int(row["llm_call_count"]),
            review_count=int(row["review_count"]),
        )

    async def query_history(
        self,
        filters: UsageFilters,
        *,
        metric_key: str,
    ) -> list[UsageHistoryPoint]:
        where_sql, args = _build_where_clause(filters, start_index=1)
        if metric_key == "review_count":
            value_expr = "COUNT(DISTINCT review_id)::double precision"
            sample_expr = "COUNT(DISTINCT review_id)::int"
        elif metric_key == "llm_call_count":
            value_expr = "COUNT(*)::double precision"
            sample_expr = "COUNT(*)::int"
        elif metric_key == "input_tokens":
            value_expr = "COALESCE(SUM(input_tokens), 0)::double precision"
            sample_expr = "COUNT(*)::int"
        elif metric_key == "output_tokens":
            value_expr = "COALESCE(SUM(output_tokens), 0)::double precision"
            sample_expr = "COUNT(*)::int"
        else:
            value_expr = "COALESCE(SUM(total_tokens), 0)::double precision"
            sample_expr = "COUNT(*)::int"

        rows = await self._conn.fetch(
            f"""
            SELECT
                date_trunc('day', occurred_at AT TIME ZONE 'UTC') AS day_start,
                {value_expr} AS metric_value,
                {sample_expr} AS sample_size
            FROM llm_token_usage
            WHERE {where_sql}
            GROUP BY 1
            ORDER BY 1 ASC
            """,
            *args,
        )
        points: list[UsageHistoryPoint] = []
        for row in rows:
            day_start = row["day_start"]
            day_end = day_start.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            points.append(
                UsageHistoryPoint(
                    window_start=day_start,
                    window_end=day_end,
                    metric_value_num=float(row["metric_value"]),
                    sample_size=int(row["sample_size"]),
                )
            )
        return points

    async def query_breakdown(
        self,
        filters: UsageFilters,
        *,
        group_by: str,
    ) -> list[UsageBreakdownRow]:
        where_sql, args = _build_where_clause(filters, start_index=1)
        if group_by == "team":
            query = f"""
                SELECT
                    u.team_id::text AS dimension_id,
                    COALESCE(t.name, 'Unknown team') AS dimension_label,
                    COUNT(DISTINCT u.review_id)::int AS review_count,
                    COUNT(*)::int AS llm_call_count,
                    COALESCE(SUM(u.input_tokens), 0)::bigint AS input_tokens,
                    COALESCE(SUM(u.output_tokens), 0)::bigint AS output_tokens,
                    COALESCE(SUM(u.total_tokens), 0)::bigint AS total_tokens
                FROM llm_token_usage u
                LEFT JOIN teams t ON t.id = u.team_id
                WHERE {where_sql}
                GROUP BY u.team_id, t.name
                ORDER BY total_tokens DESC
            """
        elif group_by == "repo":
            query = f"""
                SELECT
                    u.repo_integration_id::text AS dimension_id,
                    COALESCE(ri.repo_full_name, ri.name, 'Unknown repository')
                        AS dimension_label,
                    COUNT(DISTINCT u.review_id)::int AS review_count,
                    COUNT(*)::int AS llm_call_count,
                    COALESCE(SUM(u.input_tokens), 0)::bigint AS input_tokens,
                    COALESCE(SUM(u.output_tokens), 0)::bigint AS output_tokens,
                    COALESCE(SUM(u.total_tokens), 0)::bigint AS total_tokens
                FROM llm_token_usage u
                LEFT JOIN repo_integrations ri ON ri.id = u.repo_integration_id
                WHERE {where_sql}
                GROUP BY u.repo_integration_id, ri.repo_full_name, ri.name
                ORDER BY total_tokens DESC
            """
        elif group_by == "llm_provider":
            query = f"""
                SELECT
                    u.llm_provider_id::text AS dimension_id,
                    COALESCE(lp.name, 'Unknown provider') AS dimension_label,
                    COUNT(DISTINCT u.review_id)::int AS review_count,
                    COUNT(*)::int AS llm_call_count,
                    COALESCE(SUM(u.input_tokens), 0)::bigint AS input_tokens,
                    COALESCE(SUM(u.output_tokens), 0)::bigint AS output_tokens,
                    COALESCE(SUM(u.total_tokens), 0)::bigint AS total_tokens
                FROM llm_token_usage u
                LEFT JOIN llm_providers lp ON lp.id = u.llm_provider_id
                WHERE {where_sql}
                GROUP BY u.llm_provider_id, lp.name
                ORDER BY total_tokens DESC
            """
        else:
            msg = f"Unsupported group_by: {group_by}"
            raise ValueError(msg)

        rows = await self._conn.fetch(query, *args)
        total_sum = sum(int(row["total_tokens"]) for row in rows)
        return [
            UsageBreakdownRow(
                dimension_id=str(row["dimension_id"] or ""),
                dimension_label=str(row["dimension_label"]),
                review_count=int(row["review_count"]),
                llm_call_count=int(row["llm_call_count"]),
                input_tokens=int(row["input_tokens"]),
                output_tokens=int(row["output_tokens"]),
                total_tokens=int(row["total_tokens"]),
                percent_of_total=(
                    (int(row["total_tokens"]) / total_sum * 100.0) if total_sum else 0.0
                ),
            )
            for row in rows
        ]

    async def list_usage_events_between(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> list[LlmTokenUsageRow]:
        rows = await self._conn.fetch(
            """
            SELECT
                id, review_id, team_id, repo_integration_id, llm_provider_id,
                git_provider, model, call_index, input_tokens, output_tokens,
                total_tokens, reason, occurred_at, created_at
            FROM llm_token_usage
            WHERE occurred_at >= $1 AND occurred_at < $2
            ORDER BY occurred_at ASC
            """,
            window_start,
            window_end,
        )
        return [_row_to_llm_token_usage(row) for row in rows]

    async def upsert_daily_metrics(self, rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0
        count = 0
        for row in rows:
            await self._conn.execute(
                """
                INSERT INTO usage_metrics_daily (
                    metric_key, granularity, window_start, window_end,
                    dimension_key, team_id, repo_integration_id, llm_provider_id,
                    git_provider, metric_value_num, sample_size, job_run_id
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                )
                ON CONFLICT (metric_key, granularity, window_start, dimension_key)
                DO UPDATE SET
                    window_end = EXCLUDED.window_end,
                    team_id = EXCLUDED.team_id,
                    repo_integration_id = EXCLUDED.repo_integration_id,
                    llm_provider_id = EXCLUDED.llm_provider_id,
                    git_provider = EXCLUDED.git_provider,
                    metric_value_num = EXCLUDED.metric_value_num,
                    sample_size = EXCLUDED.sample_size,
                    job_run_id = EXCLUDED.job_run_id,
                    computed_at = now()
                """,
                row["metric_key"],
                row["granularity"],
                row["window_start"],
                row["window_end"],
                row["dimension_key"],
                row.get("team_id"),
                row.get("repo_integration_id"),
                row.get("llm_provider_id"),
                row.get("git_provider", ""),
                row["metric_value_num"],
                row["sample_size"],
                row["job_run_id"],
            )
            count += 1
        return count


def _build_where_clause(
    filters: UsageFilters,
    *,
    start_index: int,
) -> tuple[str, list[object]]:
    clauses = ["1=1"]
    args: list[object] = []
    idx = start_index

    if filters.team_id is not None:
        clauses.append(f"team_id = ${idx}")
        args.append(filters.team_id)
        idx += 1
    if filters.repo_integration_id is not None:
        clauses.append(f"repo_integration_id = ${idx}")
        args.append(filters.repo_integration_id)
        idx += 1
    if filters.git_provider:
        clauses.append(f"git_provider = ${idx}")
        args.append(filters.git_provider)
        idx += 1
    if filters.llm_provider_id is not None:
        clauses.append(f"llm_provider_id = ${idx}")
        args.append(filters.llm_provider_id)
        idx += 1
    if filters.start is not None:
        clauses.append(f"occurred_at >= ${idx}")
        args.append(filters.start)
        idx += 1
    if filters.end is not None:
        clauses.append(f"occurred_at <= ${idx}")
        args.append(filters.end)
        idx += 1

    return " AND ".join(clauses), args


def _row_to_llm_token_usage(row: asyncpg.Record) -> LlmTokenUsageRow:
    return LlmTokenUsageRow(
        id=row["id"],
        review_id=row["review_id"],
        team_id=row["team_id"],
        repo_integration_id=row["repo_integration_id"],
        llm_provider_id=row["llm_provider_id"],
        git_provider=row["git_provider"],
        model=row["model"],
        call_index=row["call_index"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        total_tokens=row["total_tokens"],
        reason=row["reason"],
        occurred_at=row["occurred_at"],
        created_at=row["created_at"],
    )
