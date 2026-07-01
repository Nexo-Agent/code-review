from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import require_org_action_dep
from app.dependencies import get_conn
from app.rbac.catalog import ActionKey
from app.repositories.usage import UsageFilters, UsageRepository
from app.schemas.usage import (
    UsageBreakdownItemResponse,
    UsageBreakdownResponse,
    UsageHistoryPointResponse,
    UsageHistoryResponse,
    UsageSummaryResponse,
)

router = APIRouter()

_USAGE_METRICS = frozenset(
    {
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "llm_call_count",
        "review_count",
    }
)


def _parse_window(
    start: datetime | None,
    end: datetime | None,
    *,
    default_days: int = 30,
) -> tuple[datetime, datetime]:
    resolved_end = (end or datetime.now(tz=UTC)).astimezone(UTC)
    resolved_start = (
        start.astimezone(UTC)
        if start is not None
        else resolved_end - timedelta(days=default_days)
    )
    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start must be before or equal to end",
        )
    return resolved_start, resolved_end


def _build_filters(
    *,
    team_id: UUID | None,
    repo_integration_id: UUID | None,
    git_provider: str | None,
    llm_provider_id: UUID | None,
    start: datetime | None,
    end: datetime | None,
) -> UsageFilters:
    window_start, window_end = _parse_window(start, end)
    return UsageFilters(
        team_id=team_id,
        repo_integration_id=repo_integration_id,
        git_provider=git_provider or None,
        llm_provider_id=llm_provider_id,
        start=window_start,
        end=window_end,
    )


@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    team_id: UUID | None = Query(None),
    repo_integration_id: UUID | None = Query(None),
    git_provider: str | None = Query(None),
    llm_provider_id: UUID | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_USAGE_READ)),
) -> UsageSummaryResponse:
    filters = _build_filters(
        team_id=team_id,
        repo_integration_id=repo_integration_id,
        git_provider=git_provider,
        llm_provider_id=llm_provider_id,
        start=start,
        end=end,
    )
    summary = await UsageRepository(conn).query_summary(filters)
    assert filters.start is not None and filters.end is not None
    return UsageSummaryResponse(
        total_tokens=summary.total_tokens,
        input_tokens=summary.input_tokens,
        output_tokens=summary.output_tokens,
        llm_call_count=summary.llm_call_count,
        review_count=summary.review_count,
        window_start=filters.start,
        window_end=filters.end,
    )


@router.get("/history", response_model=UsageHistoryResponse)
async def get_usage_history(
    metric: str = Query("total_tokens"),
    team_id: UUID | None = Query(None),
    repo_integration_id: UUID | None = Query(None),
    git_provider: str | None = Query(None),
    llm_provider_id: UUID | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_USAGE_READ)),
) -> UsageHistoryResponse:
    if metric not in _USAGE_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported metric: {metric}",
        )
    filters = _build_filters(
        team_id=team_id,
        repo_integration_id=repo_integration_id,
        git_provider=git_provider,
        llm_provider_id=llm_provider_id,
        start=start,
        end=end,
    )
    points = await UsageRepository(conn).query_history(filters, metric_key=metric)
    assert filters.start is not None and filters.end is not None
    return UsageHistoryResponse(
        metric_key=metric,
        window_start=filters.start,
        window_end=filters.end,
        points=[
            UsageHistoryPointResponse(
                window_start=point.window_start,
                window_end=point.window_end,
                metric_value_num=point.metric_value_num,
                sample_size=point.sample_size,
            )
            for point in points
        ],
    )


@router.get("/breakdown", response_model=UsageBreakdownResponse)
async def get_usage_breakdown(
    group_by: str = Query("team", pattern="^(team|repo|llm_provider)$"),
    team_id: UUID | None = Query(None),
    repo_integration_id: UUID | None = Query(None),
    git_provider: str | None = Query(None),
    llm_provider_id: UUID | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
    _admin=Depends(require_org_action_dep(ActionKey.SETTINGS_USAGE_READ)),
) -> UsageBreakdownResponse:
    filters = _build_filters(
        team_id=team_id,
        repo_integration_id=repo_integration_id,
        git_provider=git_provider,
        llm_provider_id=llm_provider_id,
        start=start,
        end=end,
    )
    rows = await UsageRepository(conn).query_breakdown(filters, group_by=group_by)
    assert filters.start is not None and filters.end is not None
    return UsageBreakdownResponse(
        group_by=group_by,
        window_start=filters.start,
        window_end=filters.end,
        items=[
            UsageBreakdownItemResponse(
                dimension_id=row.dimension_id,
                dimension_label=row.dimension_label,
                review_count=row.review_count,
                llm_call_count=row.llm_call_count,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                total_tokens=row.total_tokens,
                percent_of_total=row.percent_of_total,
            )
            for row in rows
        ],
    )
