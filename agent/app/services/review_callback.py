from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

import httpx
from coreview_shared.auth.callback_hmac import sign_payload
from coreview_shared.protocols import PRMetadata, ReviewFinding
from coreview_shared.schemas.review_callback import (
    ReviewCallbackAgent,
    ReviewCallbackError,
    ReviewCallbackEvent,
    ReviewCallbackEventType,
    ReviewCallbackFinding,
    ReviewCallbackRequest,
    ReviewCallbackResult,
)

from app.config import AgentSettings, get_agent_settings, get_settings

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Review-Signature-256"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)


def parse_callback_metadata(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid COGITO_REVIEW_CALLBACK_METADATA JSON; using empty dict")
        return {}
    return parsed if isinstance(parsed, dict) else {}


def request_from_env(settings: AgentSettings) -> ReviewCallbackRequest:
    return ReviewCallbackRequest(
        git_provider=settings.git_provider,
        repo_full_name=settings.repo_full_name,
        pr_number=settings.pr_number,
        head_sha=settings.head_sha,
    )


def request_from_metadata(
    metadata: PRMetadata, git_provider: str
) -> ReviewCallbackRequest:
    return ReviewCallbackRequest(
        git_provider=git_provider,
        repo_full_name=metadata.repo_full_name,
        pr_number=metadata.pr_number,
        head_sha=metadata.head_sha,
        base_sha=metadata.base_sha,
        head_ref=metadata.head_ref,
        base_ref=metadata.base_ref,
        pr_title=metadata.title,
        pr_url=metadata.html_url,
        pr_author=metadata.author,
    )


def findings_to_callback(findings: list[ReviewFinding]) -> list[ReviewCallbackFinding]:
    return [
        ReviewCallbackFinding(
            severity=f.severity,
            title=f.title,
            body=f.body,
            file_path=f.file_path,
            line_start=f.line_start,
            line_end=f.line_end,
        )
        for f in findings
    ]


class ReviewCallbackClient:
    def __init__(
        self,
        *,
        url: str,
        secret: str,
        metadata: dict | None = None,
        agent_name: str = "cogito-review-agent",
        agent_version: str | None = None,
    ) -> None:
        self._url = url
        self._secret = secret
        self._metadata = metadata or {}
        self._agent = ReviewCallbackAgent(
            name=agent_name,
            version=agent_version or get_settings().app_version,
        )

    @classmethod
    def from_settings(
        cls, settings: AgentSettings | None = None
    ) -> ReviewCallbackClient:
        cfg = settings or get_agent_settings()
        return cls(
            url=cfg.callback_url,
            secret=cfg.callback_secret,
            metadata=parse_callback_metadata(cfg.callback_metadata),
        )

    def build_event(
        self,
        event: ReviewCallbackEventType,
        *,
        review_id: str,
        request: ReviewCallbackRequest,
        result: ReviewCallbackResult | None = None,
        error: ReviewCallbackError | None = None,
    ) -> ReviewCallbackEvent:
        return ReviewCallbackEvent(
            event=event,
            review_id=review_id,
            occurred_at=datetime.now(tz=UTC),
            agent=self._agent,
            request=request,
            result=result,
            error=error,
            metadata=dict(self._metadata),
        )

    async def post_event(self, payload: ReviewCallbackEvent) -> None:
        body = json.dumps(
            payload.model_dump(mode="json"),
            separators=(",", ":"),
        ).encode()
        headers = {
            "Content-Type": "application/json",
            SIGNATURE_HEADER: sign_payload(body, self._secret),
        }

        last_error: Exception | None = None
        for attempt, delay in enumerate(RETRY_BACKOFF_SECONDS):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self._url, content=body, headers=headers
                    )
                if response.status_code < 500:
                    if response.status_code >= 400:
                        msg = (
                            f"Review callback rejected ({response.status_code}): "
                            f"{response.text[:200]}"
                        )
                        raise RuntimeError(msg)
                    return
                last_error = RuntimeError(
                    f"Review callback server error ({response.status_code})"
                )
            except httpx.HTTPError as exc:
                last_error = exc

            if attempt < len(RETRY_BACKOFF_SECONDS) - 1:
                logger.warning(
                    "Review callback attempt %d failed; retrying in %.1fs",
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)

        msg = f"Review callback failed after {MAX_RETRIES} attempts"
        raise RuntimeError(msg) from last_error
