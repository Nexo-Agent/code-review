import logging

import asyncpg

from app.config import get_settings
from app.providers.factory import get_providers
from app.services.review_job_prepare import prepare_review_job

logger = logging.getLogger(__name__)


async def dispatch_review_job(review_id: str) -> None:
    """Load review config from DB and spawn a one-shot agent container."""
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        request = await prepare_review_job(conn, review_id)
    finally:
        await conn.close()

    runtime = get_providers().runtime
    await runtime.run_review_job(request)
    logger.info("Review %s finished in agent container", review_id)
