import logging

from coreview_shared.agent.factory import build_review_agent
from coreview_shared.agent.models import LlmCallUsage
from coreview_shared.schemas.review_callback import (
    ReviewCallbackLlmCallUsage,
    ReviewCallbackTokenUsage,
)

from app.config import clear_agent_settings_cache, get_agent_settings
from app.services.review_context import build_review_context, cleanup_review_context
from app.services.review_reporter import ReviewReporter

logger = logging.getLogger(__name__)


def _build_token_usage(
    context,
    llm_calls: tuple[LlmCallUsage, ...],
) -> ReviewCallbackTokenUsage | None:
    if not llm_calls:
        return None
    config = context.agent_config
    return ReviewCallbackTokenUsage(
        llm_provider_id=str(getattr(config, "llm_provider_id", "")),
        model=str(getattr(config, "model", "")),
        calls=[
            ReviewCallbackLlmCallUsage(
                call_index=call.call_index,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                total_tokens=call.total_tokens,
                reason=call.reason,
            )
            for call in llm_calls
        ],
    )


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
        run_result = await review_agent.run_review(
            context.prepared_review.workspace.workspace,
            context.prepared_review.context,
        )
        findings = list(run_result.findings)
        token_usage = _build_token_usage(context, run_result.llm_calls)
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
            token_usage=token_usage,
        )
        logger.info("Review %s completed with %d findings", review_id, len(findings))
    except Exception as exc:
        logger.exception("Review %s failed", review_id)
        if context is not None:
            try:
                token_usage = None
                if review_agent is not None and hasattr(review_agent, "_llm_calls"):
                    calls = getattr(review_agent, "_llm_calls", [])
                    token_usage = _build_token_usage(context, tuple(calls))
                await reporter.send_callback(
                    "review.failed",
                    context,
                    error=exc,
                    token_usage=token_usage,
                )
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
