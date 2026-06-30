import logging

from coreview_shared.agent.factory import build_review_agent

from app.config import clear_agent_settings_cache, get_agent_settings
from app.services.review_context import build_review_context, cleanup_review_context
from app.services.review_reporter import ReviewReporter

logger = logging.getLogger(__name__)


async def execute_review_logic(review_id: str) -> None:
    clear_agent_settings_cache()
    infra = get_agent_settings()
    if not infra.review_id.strip():
        infra = infra.model_copy(update={"review_id": review_id})
    context = None
    review_agent = None
    reporter = ReviewReporter()
    try:
        context = await build_review_context(review_id, infra)
        if context.prepared_review is None:
            msg = "Prepared review was not created"
            raise RuntimeError(msg)
        review_agent = build_review_agent(context.agent_kind, context.agent_config)
        await reporter.send_callback("review.started", context)
        await review_agent.setup()
        logger.info("Review %s: running LLM review", review_id)
        findings = await review_agent.run_review(
            context.prepared_review.workspace.workspace,
            context.prepared_review.context,
        )
        logger.info(
            "Review %s: posting %d finding(s) to remote",
            review_id,
            len(findings),
        )
        publish_result = await reporter.post_comments(context, findings)
        await reporter.send_callback(
            "review.completed",
            context,
            findings=findings,
            publish_result=publish_result,
        )
        logger.info("Review %s completed with %d findings", review_id, len(findings))
    except Exception as exc:
        logger.exception("Review %s failed", review_id)
        if context is not None:
            try:
                await reporter.send_callback("review.failed", context, error=exc)
            except Exception:
                logger.exception("Failed to send review.failed callback")
        raise
    finally:
        if review_agent is not None:
            try:
                await review_agent.teardown()
            except Exception:
                logger.exception("Failed to teardown review agent")
        if context is not None and context.prepared_review is not None:
            try:
                await cleanup_review_context(context)
            except Exception:
                logger.exception(
                    "Failed to cleanup worktree %s",
                    context.prepared_review.workspace.worktree_path,
                )
