from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import AuthContext, assert_review_access, get_auth_context
from app.dependencies import get_conn
from app.jobs.review import run_review
from app.repositories.reviews import ReviewFindingRow, ReviewRepository, ReviewRow
from app.schemas.review import (
    ReviewFindingResponse,
    ReviewListResponse,
    ReviewResponse,
)
from app.services.review_rereview import (
    ReviewInProgressError,
    ReviewNotFoundError,
    prepare_rereview,
)

router = APIRouter()


def _to_finding_response(row: ReviewFindingRow) -> ReviewFindingResponse:
    return ReviewFindingResponse(
        id=row.id,
        severity=row.severity,
        file_path=row.file_path,
        line_start=row.line_start,
        line_end=row.line_end,
        title=row.title,
        body=row.body,
        created_at=row.created_at,
    )


def _to_review_response(
    row: ReviewRow,
    findings: list[ReviewFindingRow] | None = None,
) -> ReviewResponse:
    finding_rows = findings or []
    findings_count = len(finding_rows) if findings is not None else row.findings_count
    return ReviewResponse(
        id=row.id,
        provider=row.provider,
        repo_full_name=row.repo_full_name,
        pr_number=row.pr_number,
        pr_title=row.pr_title,
        pr_url=row.pr_url,
        pr_author=row.pr_author,
        head_sha=row.head_sha,
        base_sha=row.base_sha,
        base_ref=row.base_ref,
        head_ref=row.head_ref,
        status=row.status,
        delivery_id=row.delivery_id,
        team_id=row.team_id,
        project_id=row.project_id,
        error_message=row.error_message,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        findings_count=findings_count,
        summary_comment_posted=row.summary_comment_posted,
        inline_comments_posted=row.inline_comments_posted,
        inline_comments_skipped=row.inline_comments_skipped,
        findings=[_to_finding_response(f) for f in finding_rows],
    )


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    status_filter: str | None = Query(None, alias="status"),
    repo: str | None = Query(None, alias="repo"),
    pr: int | None = Query(None, alias="pr", ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
    auth: AuthContext = Depends(get_auth_context),
) -> ReviewListResponse:
    repo_db = ReviewRepository(conn)
    team_ids = auth.accessible_team_ids
    if not team_ids:
        return ReviewListResponse(items=[], total=0)
    rows = await repo_db.list_reviews(
        team_ids=team_ids,
        status=status_filter,
        repo_full_name=repo,
        pr_number=pr,
        limit=limit,
        offset=offset,
    )
    total = await repo_db.count_reviews(
        team_ids=team_ids,
        status=status_filter,
        repo_full_name=repo,
        pr_number=pr,
    )
    return ReviewListResponse(
        items=[_to_review_response(row) for row in rows],
        total=total,
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
    return _to_review_response(row, findings)


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
    await assert_review_access(conn, auth.user, existing.team_id)
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
