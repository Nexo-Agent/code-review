import json
import logging
from uuid import UUID

import asyncpg
from coreview_shared.providers.git.azure_devops import _organization_from_base_url
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.reviews import _to_review_response
from app.dependencies import get_conn
from app.jobs.review import run_review
from app.providers.factory import build_providers
from app.repositories.repo_integrations import RepoIntegrationRepository
from app.repositories.reviews import ReviewRepository
from app.schemas.review import ReviewResponse
from app.services.provider_resolution import (
    build_review_runtime_config,
    resolve_llm_provider_for_repo,
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


def _extract_ado_repo_full_name(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
        resource = payload.get("resource")
        if not isinstance(resource, dict):
            return None
        repository = resource.get("repository")
        if not isinstance(repository, dict):
            return None
        project = repository.get("project")
        if not isinstance(project, dict):
            return None
        repo_name = repository.get("name", "")
        project_name = project.get("name", "")
        if not repo_name or not project_name:
            return None
        containers = payload.get("resourceContainers", {})
        account = containers.get("account", {})
        base_url = account.get("baseUrl", "") if isinstance(account, dict) else ""
        organization = _organization_from_base_url(base_url)
        if not organization:
            return None
        return f"{organization}/{project_name}/{repo_name}"
    except (json.JSONDecodeError, TypeError):
        return None


def _extract_gitlab_repo_full_name(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
        project = payload.get("project")
        if isinstance(project, dict):
            path_with_namespace = project.get("path_with_namespace")
            if isinstance(path_with_namespace, str) and path_with_namespace:
                return path_with_namespace
    except (json.JSONDecodeError, TypeError):
        return None
    return None


def _assert_repo_matches_integration(
    repo_integration,
    repo_full_name: str,
) -> None:
    if not repo_integration.matches_repo(repo_full_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook repo does not match integration configuration",
        )


async def _enqueue_webhook_review(
    conn: asyncpg.Connection,
    *,
    integration_id: UUID,
    body: bytes,
    repo_full_name: str,
    headers: dict[str, str],
    auth_header: str | None,
    webhook_secret_resolver,
    expected_git_provider: str,
) -> ReviewResponse | JSONResponse:
    repo_repo = RepoIntegrationRepository(conn)
    resolved = await repo_repo.get_with_team(integration_id)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    repo_integration, team_id = resolved

    if not repo_integration.enabled:
        return JSONResponse(
            status_code=202,
            content={"detail": "repository not configured for review"},
        )
    if repo_integration.git_provider != expected_git_provider:
        return JSONResponse(
            status_code=202,
            content={"detail": "repository not configured for review"},
        )

    _assert_repo_matches_integration(repo_integration, repo_full_name)

    llm_provider = await resolve_llm_provider_for_repo(conn, repo_integration)
    if llm_provider is None:
        return JSONResponse(
            status_code=202,
            content={"detail": "no LLM provider configured"},
        )

    providers = build_providers(
        build_review_runtime_config(repo_integration, llm_provider)
    )

    webhook_secret = webhook_secret_resolver(repo_integration)
    if not providers.git.verify_webhook_signature(
        body,
        auth_header,
        webhook_secret,
        headers=headers,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    event = providers.git.parse_webhook(headers, body)
    if event is None:
        return JSONResponse(status_code=202, content={"detail": "event ignored"})

    repo_db = ReviewRepository(conn)
    if event.delivery_id:
        existing = await repo_db.get_by_delivery_id(event.delivery_id)
        if existing:
            return _to_review_response(existing)

    existing = await repo_db.get_by_repo_pr_sha(
        event.repo_full_name,
        event.pr_number,
        event.head_sha,
    )
    if existing:
        return _to_review_response(existing)

    review = await repo_db.create(
        provider=repo_integration.git_provider,
        repo_full_name=event.repo_full_name,
        pr_number=event.pr_number,
        head_sha=event.head_sha,
        delivery_id=event.delivery_id,
        repo_integration_id=repo_integration.id,
        team_id=team_id,
        pr_title=event.pr_title,
        pr_url=event.pr_url
        or providers.git.build_pr_url(event.repo_full_name, event.pr_number),
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


@router.post(
    "/github/{integration_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
)
async def github_webhook_for_integration(
    integration_id: UUID,
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

    return await _enqueue_webhook_review(
        conn,
        integration_id=integration_id,
        body=body,
        repo_full_name=repo_full_name,
        headers={
            "X-GitHub-Event": x_github_event or "",
            "X-GitHub-Delivery": x_github_delivery or "",
        },
        auth_header=x_hub_signature_256,
        webhook_secret_resolver=lambda integration: integration.github_webhook_secret,
        expected_git_provider="github",
    )


@router.post(
    "/azure-devops/{integration_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
)
async def azure_devops_webhook_for_integration(
    integration_id: UUID,
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    authorization: str | None = Header(None, alias="Authorization"),
) -> ReviewResponse | JSONResponse:
    body = await request.body()
    repo_full_name = _extract_ado_repo_full_name(body)
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid webhook payload",
        )

    return await _enqueue_webhook_review(
        conn,
        integration_id=integration_id,
        body=body,
        repo_full_name=repo_full_name,
        headers={},
        auth_header=authorization,
        webhook_secret_resolver=lambda integration: (
            f"{integration.ado_webhook_username}:{integration.ado_webhook_password}"
        ),
        expected_git_provider="azure-devops",
    )


@router.post(
    "/gitlab/{integration_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
)
async def gitlab_webhook_for_integration(
    integration_id: UUID,
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    x_gitlab_event: str | None = Header(None, alias="X-Gitlab-Event"),
    x_gitlab_event_uuid: str | None = Header(None, alias="X-Gitlab-Event-UUID"),
    x_gitlab_token: str | None = Header(None, alias="X-Gitlab-Token"),
    webhook_id: str | None = Header(None, alias="webhook-id"),
    webhook_timestamp: str | None = Header(None, alias="webhook-timestamp"),
    webhook_signature: str | None = Header(None, alias="webhook-signature"),
) -> ReviewResponse | JSONResponse:
    body = await request.body()
    repo_full_name = _extract_gitlab_repo_full_name(body)
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid webhook payload",
        )

    return await _enqueue_webhook_review(
        conn,
        integration_id=integration_id,
        body=body,
        repo_full_name=repo_full_name,
        headers={
            "X-Gitlab-Event": x_gitlab_event or "",
            "X-Gitlab-Event-UUID": x_gitlab_event_uuid or "",
            "webhook-id": webhook_id or "",
            "webhook-timestamp": webhook_timestamp or "",
            "webhook-signature": webhook_signature or "",
            "X-Gitlab-Token": x_gitlab_token or "",
        },
        auth_header=webhook_signature or x_gitlab_token,
        webhook_secret_resolver=lambda integration: integration.gitlab_webhook_secret,
        expected_git_provider="gitlab",
    )


@router.post("/github", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def github_webhook_legacy(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> JSONResponse:
    logger.warning("Deprecated global GitHub webhook endpoint used")
    return JSONResponse(
        status_code=410,
        content={
            "detail": (
                "Use per-integration webhook URL: "
                "/api/v1/webhooks/github/{integration_id}"
            )
        },
    )


@router.post("/azure-devops", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def azure_devops_webhook_legacy(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> JSONResponse:
    logger.warning("Deprecated global Azure DevOps webhook endpoint used")
    return JSONResponse(
        status_code=410,
        content={
            "detail": (
                "Use per-integration webhook URL: "
                "/api/v1/webhooks/azure-devops/{integration_id}"
            )
        },
    )


@router.post("/gitlab", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def gitlab_webhook_legacy(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> JSONResponse:
    logger.warning("Deprecated global GitLab webhook endpoint used")
    return JSONResponse(
        status_code=410,
        content={
            "detail": (
                "Use per-integration webhook URL: "
                "/api/v1/webhooks/gitlab/{integration_id}"
            )
        },
    )


@router.post(
    "/bitbucket/{integration_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
)
async def bitbucket_webhook_for_integration(
    integration_id: UUID,
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    x_event_key: str | None = Header(None, alias="X-Event-Key"),
    x_hub_signature: str | None = Header(None, alias="X-Hub-Signature"),
    x_hook_uuid: str | None = Header(None, alias="X-Hook-UUID"),
    x_request_uuid: str | None = Header(None, alias="X-Request-UUID"),
) -> ReviewResponse | JSONResponse:
    body = await request.body()
    repo_full_name = _extract_repo_full_name(body)
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid webhook payload",
        )

    return await _enqueue_webhook_review(
        conn,
        integration_id=integration_id,
        body=body,
        repo_full_name=repo_full_name,
        headers={
            "X-Event-Key": x_event_key or "",
            "X-Hook-UUID": x_hook_uuid or "",
            "X-Request-UUID": x_request_uuid or "",
        },
        auth_header=x_hub_signature,
        webhook_secret_resolver=(
            lambda integration: integration.bitbucket_webhook_secret
        ),
        expected_git_provider="bitbucket",
    )


def _extract_bitbucket_dc_repo_full_name(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
        pull_request = payload.get("pullRequest")
        if not isinstance(pull_request, dict):
            return None
        to_ref = pull_request.get("toRef")
        if not isinstance(to_ref, dict):
            return None
        repository = to_ref.get("repository")
        if not isinstance(repository, dict):
            return None
        project = repository.get("project")
        if not isinstance(project, dict):
            return None
        project_key = project.get("key", "")
        repo_slug = repository.get("slug", "")
        if not project_key or not repo_slug:
            return None
        return f"{project_key}/{repo_slug}"
    except (json.JSONDecodeError, TypeError):
        return None


@router.post(
    "/bitbucket-dc/{integration_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
)
async def bitbucket_dc_webhook_for_integration(
    integration_id: UUID,
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
    authorization: str | None = Header(None, alias="Authorization"),
    x_event_key: str | None = Header(None, alias="X-Event-Key"),
    x_request_id: str | None = Header(None, alias="X-Request-Id"),
) -> ReviewResponse | JSONResponse:
    body = await request.body()
    repo_full_name = _extract_bitbucket_dc_repo_full_name(body)
    if not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid webhook payload",
        )

    return await _enqueue_webhook_review(
        conn,
        integration_id=integration_id,
        body=body,
        repo_full_name=repo_full_name,
        headers={
            "X-Event-Key": x_event_key or "",
            "X-Request-Id": x_request_id or "",
        },
        auth_header=authorization,
        webhook_secret_resolver=lambda integration: (
            f"{integration.bitbucket_dc_webhook_username}:"
            f"{integration.bitbucket_dc_webhook_password}"
        ),
        expected_git_provider="bitbucket-dc",
    )


@router.post("/bitbucket", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def bitbucket_webhook_legacy(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> JSONResponse:
    logger.warning("Deprecated global Bitbucket webhook endpoint used")
    return JSONResponse(
        status_code=410,
        content={
            "detail": (
                "Use per-integration webhook URL: "
                "/api/v1/webhooks/bitbucket/{integration_id}"
            )
        },
    )


@router.post("/bitbucket-dc", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def bitbucket_dc_webhook_legacy(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> JSONResponse:
    logger.warning("Deprecated global Bitbucket DC webhook endpoint used")
    return JSONResponse(
        status_code=410,
        content={
            "detail": (
                "Use per-integration webhook URL: "
                "/api/v1/webhooks/bitbucket-dc/{integration_id}"
            )
        },
    )
