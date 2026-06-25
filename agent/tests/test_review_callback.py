import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from coreview_shared.auth.callback_hmac import sign_payload, verify_payload_signature
from coreview_shared.schemas.review_callback import (
    ReviewCallbackError,
    ReviewCallbackRequest,
)

from app.services.review_callback import ReviewCallbackClient


def test_sign_payload_matches_hmac_sha256() -> None:
    body = b'{"event":"review.started"}'
    secret = "shared-secret"
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sign_payload(body, secret) == expected


def test_verify_payload_signature_rejects_invalid() -> None:
    body = b"payload"
    assert not verify_payload_signature(body, "sha256=bad", "secret")
    assert not verify_payload_signature(body, None, "secret")


def test_review_callback_client_serializes_event() -> None:
    client = ReviewCallbackClient(
        url="http://callback.test/events",
        secret="secret",
        metadata={"delivery_id": "d1"},
        agent_version="0.1.0",
    )
    request = ReviewCallbackRequest(
        git_provider="github",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="abc",
    )
    event = client.build_event(
        "review.started",
        review_id="550e8400-e29b-41d4-a716-446655440000",
        request=request,
    )
    dumped = json.loads(event.model_dump_json())
    assert dumped["schema_version"] == "1.0"
    assert dumped["event"] == "review.started"
    assert dumped["metadata"]["delivery_id"] == "d1"


@pytest.mark.asyncio
async def test_review_callback_client_posts_with_signature() -> None:
    client = ReviewCallbackClient(
        url="http://callback.test/events",
        secret="secret",
    )
    request = ReviewCallbackRequest(
        git_provider="github",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="abc",
    )
    event = client.build_event(
        "review.completed",
        review_id="550e8400-e29b-41d4-a716-446655440000",
        request=request,
    )

    mock_response = MagicMock()
    mock_response.status_code = 204

    mock_http = AsyncMock()
    mock_http.post.return_value = mock_response
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch(
        "app.services.review_callback.httpx.AsyncClient",
        return_value=mock_http,
    ):
        await client.post_event(event)

    call_kwargs = mock_http.post.call_args.kwargs
    assert call_kwargs["content"]
    assert call_kwargs["headers"]["X-Review-Signature-256"].startswith("sha256=")


@pytest.mark.asyncio
async def test_review_callback_client_retries_on_5xx() -> None:
    client = ReviewCallbackClient(
        url="http://callback.test/events",
        secret="secret",
    )
    request = ReviewCallbackRequest(
        git_provider="github",
        repo_full_name="org/repo",
        pr_number=1,
        head_sha="abc",
    )
    event = client.build_event(
        "review.failed",
        review_id="550e8400-e29b-41d4-a716-446655440000",
        request=request,
        error=ReviewCallbackError(message="boom"),
    )

    fail_response = MagicMock(status_code=503, text="unavailable")
    ok_response = MagicMock(status_code=204)

    mock_http = AsyncMock()
    mock_http.post.side_effect = [fail_response, ok_response]
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with (
        patch("app.services.review_callback.httpx.AsyncClient", return_value=mock_http),
        patch("app.services.review_callback.asyncio.sleep", new=AsyncMock()),
    ):
        await client.post_event(event)

    assert mock_http.post.await_count == 2
