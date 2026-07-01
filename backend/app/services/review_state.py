from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.repositories.reviews import ReviewRow

IN_PROGRESS_REVIEW_STATUSES = {"pending", "running"}
STALE_REVIEW_GRACE_SECONDS = 120


def is_review_in_progress(review: ReviewRow) -> bool:
    return review.status in IN_PROGRESS_REVIEW_STATUSES


def is_review_stale(
    review: ReviewRow,
    *,
    timeout_seconds: int,
    now: datetime | None = None,
) -> bool:
    if not is_review_in_progress(review):
        return False

    now = now or datetime.now(tz=UTC)
    anchor = review.started_at or review.created_at
    deadline = anchor + timedelta(
        seconds=max(timeout_seconds, 0) + STALE_REVIEW_GRACE_SECONDS
    )
    return now >= deadline
