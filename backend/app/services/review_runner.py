import asyncio
import logging

from app.services.review_spawn import run_review_agent_container

logger = logging.getLogger(__name__)


async def execute_review_logic(review_id: str) -> None:
    """Delegate review execution to a one-shot agent container."""
    await asyncio.to_thread(run_review_agent_container, review_id)
    logger.info("Review %s finished in agent container", review_id)
