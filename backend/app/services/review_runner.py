import logging

import asyncpg

from app.config import get_code_review_settings, get_settings
from app.providers.factory import build_runtime_provider
from app.services.review_job_prepare import prepare_review_execution

logger = logging.getLogger(__name__)


async def dispatch_review_job(review_id: str) -> bool:
    """Load review config from DB and submit execution to the configured backend.

    Returns True when the worker should wait for agent completion (Docker mode).
    Returns False when submission is async (Kubernetes mode).
    """
    settings = get_settings()
    infra = get_code_review_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        request = await prepare_review_execution(conn, review_id)
    finally:
        await conn.close()

    runtime = build_runtime_provider(infra=infra, app_settings=settings)
    result = await runtime.submit_execution(request)
    if not result.accepted:
        msg = f"Execution submission rejected for review {review_id}"
        raise RuntimeError(msg)

    if result.waits_for_completion:
        logger.info("Review %s finished in agent container", review_id)
    else:
        logger.info(
            "Review %s submitted to %s (%s)",
            review_id,
            result.backend_kind,
            result.external_ref,
        )
    return result.waits_for_completion
