from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_conn
from app.jobs.review import run_review
from app.repositories.reviews import ReviewFindingRow, ReviewRepository, ReviewRow
from app.schemas.review import (
    ReviewFindingResponse,
    ReviewListResponse,
    ReviewResponse,
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
    return ReviewResponse(
        id=row.id,
        provider=row.provider,
        repo_full_name=row.repo_full_name,
        pr_number=row.pr_number,
        head_sha=row.head_sha,
        status=row.status,
        delivery_id=row.delivery_id,
        error_message=row.error_message,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        findings=[_to_finding_response(f) for f in (findings or [])],
    )


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    status_filter: str | None = Query(None, alias="status"),
    repo: str | None = Query(None, alias="repo"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
) -> ReviewListResponse:
    repo_db = ReviewRepository(conn)
    rows = await repo_db.list_reviews(
        status=status_filter,
        repo_full_name=repo,
        limit=limit,
        offset=offset,
    )
    return ReviewListResponse(
        items=[_to_review_response(row) for row in rows],
        total=len(rows),
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> ReviewResponse:
    repo_db = ReviewRepository(conn)
    row = await repo_db.get(review_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    findings = await repo_db.list_findings(review_id)
    return _to_review_response(row, findings)


@router.post("/{review_id}/retry", response_model=ReviewResponse)
async def retry_review(
    review_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> ReviewResponse:
    repo_db = ReviewRepository(conn)
    row = await repo_db.get(review_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if row.status not in {"failed", "completed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review is not retryable",
        )
    updated = await repo_db.reset_for_retry(review_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    run_review.delay(str(review_id))
    return _to_review_response(updated)
