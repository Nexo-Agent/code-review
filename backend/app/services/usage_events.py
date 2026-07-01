from __future__ import annotations

import logging
from uuid import UUID

from coreview_shared.schemas.review_callback import ReviewCallbackEvent

from app.repositories.repo_integrations import RepoIntegrationRepository
from app.repositories.reviews import ReviewRow
from app.repositories.usage import UsageRepository
from app.services.provider_resolution import resolve_llm_provider_for_repo

logger = logging.getLogger(__name__)


async def persist_token_usage_from_callback(
    conn,
    *,
    review: ReviewRow,
    event: ReviewCallbackEvent,
) -> int:
    if event.token_usage is None or not event.token_usage.calls:
        return 0

    repo_integration = None
    git_provider = ""
    if review.repo_integration_id is not None:
        repo_integration = await RepoIntegrationRepository(conn).get(
            review.repo_integration_id
        )
        if repo_integration is not None:
            git_provider = repo_integration.git_provider

    llm_provider_uuid: UUID | None = None
    model = event.token_usage.model
    llm_provider = None
    if repo_integration is not None:
        llm_provider = await resolve_llm_provider_for_repo(conn, repo_integration)
        if llm_provider is not None:
            llm_provider_uuid = llm_provider.id
            if not model:
                model = llm_provider.model

    calls = [
        {
            "call_index": call.call_index,
            "input_tokens": call.input_tokens,
            "output_tokens": call.output_tokens,
            "total_tokens": call.total_tokens,
            "reason": call.reason,
        }
        for call in event.token_usage.calls
    ]
    inserted = await UsageRepository(conn).insert_llm_calls(
        review_id=review.id,
        team_id=review.team_id,
        repo_integration_id=review.repo_integration_id,
        llm_provider_id=llm_provider_uuid,
        git_provider=git_provider,
        model=model,
        occurred_at=event.occurred_at,
        calls=calls,
    )
    if inserted:
        logger.info(
            "Persisted %d LLM token usage row(s) for review %s",
            inserted,
            review.id,
        )
    return inserted
