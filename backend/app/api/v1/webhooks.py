import json
import logging

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.reviews import _to_review_response
from app.dependencies import get_conn
from app.jobs.review import run_review
from app.providers.git.github import GitHubProvider
from app.repositories.reviews import ReviewRepository
from app.schemas.review import ReviewResponse
from app.services.integration_settings import get_integration_settings

logger = logging.getLogger(__name__)

router = APIRouter()

HANDLED_ACTIONS = {"opened", "synchronize", "reopened"}


@router.post("/github", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def github_webhook(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> ReviewResponse | JSONResponse:
    integration = await get_integration_settings(conn)
    body = await request.body()

    git = GitHubProvider(token=integration.github_token)
    if not git.verify_webhook_signature(
        body,
        x_hub_signature_256,
        integration.github_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    if x_github_event != "pull_request":
        return JSONResponse(status_code=202, content={"detail": "event ignored"})

    payload = json.loads(body)
    action = payload.get("action")
    if action not in HANDLED_ACTIONS:
        return JSONResponse(status_code=202, content={"detail": "action ignored"})

    pr = payload.get("pull_request")
    repo = payload.get("repository")
    if not pr or not repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    repo_full_name = repo["full_name"]
    if not integration.accepts_repo(repo_full_name):
        return JSONResponse(
            status_code=202,
            content={"detail": "repository not configured for review"},
        )

    pr_number = pr["number"]
    head_sha = pr["head"]["sha"]

    repo_db = ReviewRepository(conn)
    if x_github_delivery:
        existing = await repo_db.get_by_delivery_id(x_github_delivery)
        if existing:
            return _to_review_response(existing)

    review = await repo_db.create(
        provider="github",
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        head_sha=head_sha,
        delivery_id=x_github_delivery,
    )

    run_review.delay(str(review.id))
    logger.info(
        "Enqueued review %s for %s#%s",
        review.id,
        repo_full_name,
        pr_number,
    )
    return _to_review_response(review)
