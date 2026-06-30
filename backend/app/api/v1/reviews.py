from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.pagination import PaginationParams
from app.auth.dependencies import (
    AuthContext,
    assert_review_access,
    get_auth_context,
    require_org_admin_user,
)
from app.dependencies import get_conn
from app.jobs.review import run_review
from app.jobs.review_analytics import recompute_review_analytics
from app.rbac.catalog import ActionKey
from app.repositories.review_analytics import ReviewAnalyticsRepository
from app.repositories.reviews import ReviewFindingRow, ReviewRepository, ReviewRow
from app.schemas.review import ReviewFindingResponse, ReviewListResponse, ReviewResponse
from app.schemas.review_analytics import (
    ReviewAnalyticsHistoryPointResponse,
    ReviewAnalyticsHistoryResponse,
    ReviewAnalyticsMetricResponse,
    ReviewAnalyticsRecomputeRequest,
    ReviewAnalyticsRecomputeResponse,
    ReviewAnalyticsSnapshotResponse,
)
from app.services.provider_resolution import build_providers_for_repo
from app.services.review_rereview import (
    ReviewInProgressError,
    ReviewNotFoundError,
    prepare_rereview,
)

router = APIRouter()


def _analytics_dimension_key(
    *,
    scope: str,
    team_id: UUID | None,
    repo_integration_id: UUID | None,
) -> str:
    if scope == "team":
        if team_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="team_id is required for team scope",
            )
        return f"team:{team_id}"
    if scope == "repo":
        if repo_integration_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="repo_integration_id is required for repo scope",
            )
        return f"repo:{repo_integration_id}"
    return "all"


def _resolve_pr_url(row: ReviewRow, git_provider=None) -> str:
    stored = row.pr_url.strip()
    if stored:
        return stored
    if git_provider is not None:
        return git_provider.build_pr_url(row.repo_full_name, row.pr_number)
    return ""


def _to_finding_response(
    row: ReviewFindingRow,
    *,
    git_provider=None,
    repo_full_name: str = "",
    head_sha: str = "",
) -> ReviewFindingResponse:
    code_url = None
    if row.file_path and git_provider is not None:
        code_url = git_provider.build_blob_url(
            repo_full_name,
            head_sha,
            row.file_path,
            row.line_start,
        )
    return ReviewFindingResponse(
        id=row.id,
        severity=row.severity,
        file_path=row.file_path,
        line_start=row.line_start,
        line_end=row.line_end,
        title=row.title,
        body=row.body,
        code_url=code_url,
        created_at=row.created_at,
    )


def _to_review_response(
    row: ReviewRow,
    findings: list[ReviewFindingRow] | None = None,
    *,
    git_provider=None,
) -> ReviewResponse:
    finding_rows = findings or []
    findings_count = len(finding_rows) if findings is not None else row.findings_count
    return ReviewResponse(
        id=row.id,
        provider=row.provider,
        repo_full_name=row.repo_full_name,
        pr_number=row.pr_number,
        pr_title=row.pr_title,
        pr_url=_resolve_pr_url(row, git_provider),
        pr_author=row.pr_author,
        head_sha=row.head_sha,
        base_sha=row.base_sha,
        base_ref=row.base_ref,
        head_ref=row.head_ref,
        status=row.status,
        delivery_id=row.delivery_id,
        repo_integration_id=row.repo_integration_id,
        team_id=row.team_id,
        error_message=row.error_message,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        findings_count=findings_count,
        summary_comment_posted=row.summary_comment_posted,
        inline_comments_posted=row.inline_comments_posted,
        inline_comments_skipped=row.inline_comments_skipped,
        findings=[
            _to_finding_response(
                f,
                git_provider=git_provider,
                repo_full_name=row.repo_full_name,
                head_sha=row.head_sha,
            )
            for f in finding_rows
        ],
    )


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    status_filter: str | None = Query(None, alias="status"),
    repo: list[str] = Query(default=[]),
    pr: int | None = Query(None, alias="pr", ge=1),
    q: str | None = Query(None, max_length=200),
    pagination: PaginationParams = Depends(),
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> ReviewListResponse:
    repo_db = ReviewRepository(conn)
    team_ids = auth.accessible_team_ids
    if not team_ids:
        return ReviewListResponse(items=[], total=0)
    search = (q or "").strip() or None
    repo_names = repo or None
    rows = await repo_db.list_reviews(
        team_ids=team_ids,
        status=status_filter,
        repo_full_names=repo_names,
        pr_number=pr,
        search=search,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    total = await repo_db.count_reviews(
        team_ids=team_ids,
        status=status_filter,
        repo_full_names=repo_names,
        pr_number=pr,
        search=search,
    )
    return ReviewListResponse(
        items=[_to_review_response(row) for row in rows],
        total=total,
    )


@router.get("/analytics", response_model=ReviewAnalyticsSnapshotResponse)
async def get_reviews_analytics(
    scope: str = Query("all", pattern="^(all|team|repo)$"),
    team_id: UUID | None = Query(None),
    repo_integration_id: UUID | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> ReviewAnalyticsSnapshotResponse:
    all_rows = await ReviewAnalyticsRepository(conn).list_latest_metric_rows(
        provider="github"
    )
    if not all_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics snapshot not found",
        )
    allowed_team_ids = set(auth.accessible_team_ids)
    rows = [
        row
        for row in all_rows
        if row.team_id is None or row.team_id in allowed_team_ids
    ]
    if scope == "team":
        rows = [
            row
            for row in rows
            if row.dimension_key == f"team:{team_id}" or row.team_id == team_id
        ]
    elif scope == "repo":
        rows = [
            row
            for row in rows
            if row.dimension_key == f"repo:{repo_integration_id}"
            or row.repo_integration_id == repo_integration_id
        ]
    latest = max(all_rows, key=lambda row: row.computed_at)
    return ReviewAnalyticsSnapshotResponse(
        job_run_id=latest.job_run_id,
        computed_at=latest.computed_at,
        window_start=latest.window_start,
        window_end=latest.window_end,
        items=[
            ReviewAnalyticsMetricResponse(
                metric_key=row.metric_key,
                provider=row.provider,
                granularity=row.granularity,
                window_start=row.window_start,
                window_end=row.window_end,
                dimension_key=row.dimension_key,
                repo_integration_id=row.repo_integration_id,
                team_id=row.team_id,
                repo_full_name=row.repo_full_name,
                metric_value_num=row.metric_value_num,
                numerator=row.numerator,
                denominator=row.denominator,
                sample_size=row.sample_size,
                dimensions_json=row.dimensions_json,
                job_run_id=row.job_run_id,
                computed_at=row.computed_at,
            )
            for row in rows
        ],
    )


@router.get("/analytics/history", response_model=ReviewAnalyticsHistoryResponse)
async def get_reviews_analytics_history(
    metric_key: str = Query(..., min_length=1),
    scope: str = Query("all", pattern="^(all|team|repo)$"),
    team_id: UUID | None = Query(None),
    repo_integration_id: UUID | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> ReviewAnalyticsHistoryResponse:
    range_end = (end or datetime.now(tz=UTC)).astimezone(UTC)
    range_start = (
        start.astimezone(UTC) if start is not None else range_end - timedelta(days=days)
    )
    if range_start > range_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start must be before end",
        )
    dimension_key = _analytics_dimension_key(
        scope=scope,
        team_id=team_id,
        repo_integration_id=repo_integration_id,
    )
    if scope == "team" and team_id not in set(auth.accessible_team_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    rows = await ReviewAnalyticsRepository(conn).list_metric_history(
        provider="github",
        metric_key=metric_key,
        dimension_key=dimension_key,
        start=range_start,
        end=range_end,
    )
    return ReviewAnalyticsHistoryResponse(
        metric_key=metric_key,
        scope=scope,
        team_id=team_id,
        repo_integration_id=repo_integration_id,
        range_start=range_start,
        range_end=range_end,
        items=[
            ReviewAnalyticsHistoryPointResponse(
                metric_key=row.metric_key,
                provider=row.provider,
                dimension_key=row.dimension_key,
                repo_integration_id=row.repo_integration_id,
                team_id=row.team_id,
                repo_full_name=row.repo_full_name,
                metric_value_num=row.metric_value_num,
                numerator=row.numerator,
                denominator=row.denominator,
                sample_size=row.sample_size,
                computed_at=row.computed_at,
                window_start=row.window_start,
                window_end=row.window_end,
            )
            for row in rows
        ],
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> ReviewResponse:
    repo_db = ReviewRepository(conn)
    row = await repo_db.get(review_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await assert_review_access(conn, auth.user, row.team_id)
    findings = await repo_db.list_findings(review_id)
    git_provider = None
    needs_provider = row.repo_integration_id is not None and (
        not row.pr_url.strip() or any(f.file_path for f in findings)
    )
    if needs_provider:
        try:
            providers = await build_providers_for_repo(
                conn,
                row.repo_full_name,
                repo_integration_id=row.repo_integration_id,
            )
            git_provider = providers.git
        except (ValueError, NotImplementedError):
            pass
    return _to_review_response(row, findings, git_provider=git_provider)


@router.post("/{review_id}/retry", response_model=ReviewResponse)
async def retry_review(
    review_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> ReviewResponse:
    repo_db = ReviewRepository(conn)
    existing = await repo_db.get(review_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await assert_review_access(
        conn, auth.user, existing.team_id, action=ActionKey.REVIEW_RERUN
    )
    try:
        review = await prepare_rereview(conn, review_id)
    except ReviewNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    except ReviewInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    run_review.delay(str(review.id))
    return _to_review_response(review)


@router.post(
    "/analytics/recompute",
    response_model=ReviewAnalyticsRecomputeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recompute_reviews_analytics(
    payload: ReviewAnalyticsRecomputeRequest,
    _admin=Depends(require_org_admin_user),
) -> ReviewAnalyticsRecomputeResponse:
    task = recompute_review_analytics.delay(
        payload.window_days,
        payload.window_end.isoformat() if payload.window_end else None,
    )
    return ReviewAnalyticsRecomputeResponse(
        task_id=task.id,
        window_days=payload.window_days,
        window_end=payload.window_end,
    )
