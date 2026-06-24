import json
import logging

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.reviews import _to_review_response
from app.dependencies import get_conn
from app.jobs.review import run_review
from app.providers.factory import build_providers
from app.repositories.reviews import ReviewRepository
from app.schemas.review import ReviewResponse
from app.services.provider_resolution import (
    build_providers_config,
    resolve_llm_provider,
    resolve_repo_integration,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_repo_full_name(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
        repo = payload.get("repository")
        if isinstance(repo, dict):
            full_name = repo.get("full_name")
            if isinstance(full_name, str) and full_name:
                return full_name
    except (json.JSONDecodeError, TypeError):
        return None
    return None


@router.post("/github", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def github_webhook(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> ReviewResponse | JSONResponse:
    body = await request.body()
    repo_full_name = _extract_repo_full_name(body)
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid webhook payload",
        )

    repo_integration = await resolve_repo_integration(conn, repo_full_name)
    if repo_integration is None or not repo_integration.enabled:
        return JSONResponse(
            status_code=202,
            content={"detail": "repository not configured for review"},
        )

    llm_provider = await resolve_llm_provider(conn, repo_integration)
    if llm_provider is None:
        return JSONResponse(
            status_code=202,
            content={"detail": "no LLM provider configured"},
        )

    providers = build_providers(build_providers_config(repo_integration, llm_provider))

    if not providers.git.verify_webhook_signature(
        body,
        x_hub_signature_256,
        repo_integration.github_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    headers = {
        "X-GitHub-Event": x_github_event or "",
        "X-GitHub-Delivery": x_github_delivery or "",
    }
    event = providers.git.parse_webhook(headers, body)
    if event is None:
        return JSONResponse(status_code=202, content={"detail": "event ignored"})

    repo_db = ReviewRepository(conn)
    if event.delivery_id:
        existing = await repo_db.get_by_delivery_id(event.delivery_id)
        if existing:
            return _to_review_response(existing)

    review = await repo_db.create(
        provider=repo_integration.git_provider,
        repo_full_name=event.repo_full_name,
        pr_number=event.pr_number,
        head_sha=event.head_sha,
        delivery_id=event.delivery_id,
        repo_integration_id=repo_integration.id,
    )

    run_review.delay(str(review.id))
    logger.info(
        "Enqueued review %s for %s#%s (integration %s)",
        review.id,
        event.repo_full_name,
        event.pr_number,
        repo_integration.id,
    )
    return _to_review_response(review)
