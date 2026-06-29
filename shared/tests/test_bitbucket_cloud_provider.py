import hashlib
import hmac
import json

import pytest

from coreview_shared.git.bitbucket_cloud import (
    BitbucketCloudProvider,
    parse_repo_full_name,
)


def _pr_payload(*, event: str = "pullrequest:created") -> dict:
    return {
        "repository": {"full_name": "acme/backend"},
        "pullrequest": {
            "id": 42,
            "title": "Add feature",
            "draft": False,
            "source": {"commit": {"hash": "abc123" * 5 + "ab"}},
            "links": {
                "html": {"href": "https://bitbucket.org/acme/backend/pull-requests/42"}
            },
        },
    }


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_parse_repo_full_name_valid() -> None:
    assert parse_repo_full_name("acme/backend") == ("acme", "backend")


def test_parse_repo_full_name_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid Bitbucket"):
        parse_repo_full_name("repo-only")


def test_bitbucket_cloud_webhook_signature_valid() -> None:
    provider = BitbucketCloudProvider(token="")
    body = b'{"test": true}'
    secret = "hook-secret"
    signature = _sign(body, secret)
    assert provider.verify_webhook_signature(body, signature, secret)


def test_bitbucket_cloud_webhook_signature_invalid() -> None:
    provider = BitbucketCloudProvider(token="")
    assert not provider.verify_webhook_signature(b"{}", "sha256=bad", "hook-secret")
    assert not provider.verify_webhook_signature(b"{}", None, "hook-secret")


def test_bitbucket_cloud_parse_webhook_created() -> None:
    provider = BitbucketCloudProvider(token="")
    body = json.dumps(_pr_payload()).encode()
    event = provider.parse_webhook(
        {"X-Event-Key": "pullrequest:created", "X-Hook-UUID": "hook-1"},
        body,
    )
    assert event is not None
    assert event.repo_full_name == "acme/backend"
    assert event.pr_number == 42
    assert event.head_sha == "abc123" * 5 + "ab"
    assert event.delivery_id == "hook-1"


def test_bitbucket_cloud_parse_webhook_ignores_merged() -> None:
    provider = BitbucketCloudProvider(token="")
    body = json.dumps(_pr_payload()).encode()
    assert (
        provider.parse_webhook({"X-Event-Key": "pullrequest:fulfilled"}, body) is None
    )


def test_bitbucket_cloud_parse_webhook_ignores_draft() -> None:
    provider = BitbucketCloudProvider(token="")
    payload = _pr_payload()
    payload["pullrequest"]["draft"] = True
    body = json.dumps(payload).encode()
    assert provider.parse_webhook({"X-Event-Key": "pullrequest:created"}, body) is None


def test_bitbucket_cloud_build_pr_url() -> None:
    provider = BitbucketCloudProvider(token="")
    assert (
        provider.build_pr_url("acme/backend", 42)
        == "https://bitbucket.org/acme/backend/pull-requests/42"
    )
