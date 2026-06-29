from uuid import UUID

from coreview_shared.review import PRMetadata

from app.repositories.reviews import ReviewRepository, ReviewRow
from app.services.provider_resolution import build_providers_for_repo


class ReviewNotFoundError(LookupError):
    pass


class ReviewInProgressError(ValueError):
    pass


async def resolve_latest_pr_metadata(
    conn,
    review: ReviewRow,
) -> PRMetadata:
    providers = await build_providers_for_repo(
        conn,
        review.repo_full_name,
        repo_integration_id=review.repo_integration_id,
    )
    return await providers.git.get_pr_metadata(review.repo_full_name, review.pr_number)


async def resolve_latest_head_sha(
    conn,
    review: ReviewRow,
) -> str:
    metadata = await resolve_latest_pr_metadata(conn, review)
    return metadata.head_sha


async def prepare_rereview(conn, review_id: UUID) -> ReviewRow:
    repo_db = ReviewRepository(conn)
    review = await repo_db.get(review_id)
    if review is None:
        raise ReviewNotFoundError(review_id)

    if review.status in {"pending", "running"}:
        msg = "Review is already in progress"
        raise ReviewInProgressError(msg)

    metadata = await resolve_latest_pr_metadata(conn, review)

    if metadata.head_sha != review.head_sha:
        return await repo_db.create(
            provider=review.provider,
            repo_full_name=review.repo_full_name,
            pr_number=review.pr_number,
            head_sha=metadata.head_sha,
            delivery_id=None,
            repo_integration_id=review.repo_integration_id,
            team_id=review.team_id,
            pr_title=metadata.title or review.pr_title,
            pr_url=metadata.html_url,
            pr_author=metadata.author,
            base_sha=metadata.base_sha,
            base_ref=metadata.base_ref,
            head_ref=metadata.head_ref,
        )

    updated = await repo_db.reset_for_retry(review_id)
    if updated is None:
        raise ReviewNotFoundError(review_id)
    return updated
