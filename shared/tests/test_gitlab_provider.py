import base64
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from coreview_shared.git.gitlab import (
    GitLabDiffRefs,
    GitLabProvider,
    normalize_gitlab_base_url,
    parse_repo_full_name,
    verify_gitlab_signing_token,
)
from coreview_shared.git.models import InlineComment


def _signing_token() -> str:
    return "whsec_" + base64.b64encode(b"test-signing-key").decode("utf-8")


def _sign_gitlab_webhook(
    body: bytes,
    signing_token: str,
    message_id: str,
    *,
    timestamp: str | None = None,
    now: float | None = None,
) -> dict[str, str]:
    ts = timestamp or str(int(now if now is not None else time.time()))
    raw_key = base64.b64decode(signing_token.removeprefix("whsec_"))
    body_text = body.decode("utf-8")
    message = f"{message_id}.{ts}.{body_text}".encode()
    digest = hmac.new(raw_key, message, hashlib.sha256).digest()
    signature = "v1," + base64.b64encode(digest).decode("utf-8")
    return {
        "webhook-id": message_id,
        "webhook-timestamp": ts,
        "webhook-signature": signature,
    }


def test_parse_repo_full_name_valid() -> None:
    assert parse_repo_full_name("group/subgroup/repo") == "group/subgroup/repo"
    assert parse_repo_full_name("acme/backend") == "acme/backend"


def test_parse_repo_full_name_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid GitLab"):
        parse_repo_full_name("repo-only")


def test_normalize_gitlab_base_url_defaults() -> None:
    assert normalize_gitlab_base_url("") == "https://gitlab.com"
    assert normalize_gitlab_base_url("https://gitlab.example.com/") == (
        "https://gitlab.example.com"
    )


def test_gitlab_webhook_token_valid() -> None:
    provider = GitLabProvider(token="")
    assert provider.verify_webhook_signature(b"{}", "my-secret", "my-secret")


def test_gitlab_webhook_token_invalid() -> None:
    provider = GitLabProvider(token="")
    assert not provider.verify_webhook_signature(b"{}", "wrong", "my-secret")
    assert not provider.verify_webhook_signature(b"{}", None, "my-secret")
    assert not provider.verify_webhook_signature(b"{}", "token", "")


def test_gitlab_webhook_signing_token_valid() -> None:
    provider = GitLabProvider(token="")
    body = b'{"object_kind":"merge_request"}'
    token = _signing_token()
    headers = _sign_gitlab_webhook(body, token, "msg-1")
    assert provider.verify_webhook_signature(
        body,
        headers["webhook-signature"],
        token,
        headers=headers,
    )


def test_gitlab_webhook_signing_token_invalid_signature() -> None:
    provider = GitLabProvider(token="")
    body = b"{}"
    token = _signing_token()
    headers = _sign_gitlab_webhook(body, token, "msg-1")
    headers["webhook-signature"] = "v1,invalid"
    assert not provider.verify_webhook_signature(
        body,
        headers["webhook-signature"],
        token,
        headers=headers,
    )


def test_gitlab_webhook_signing_token_rejects_stale_timestamp() -> None:
    provider = GitLabProvider(token="")
    body = b"{}"
    token = _signing_token()
    stale = str(int(time.time()) - 600)
    headers = _sign_gitlab_webhook(body, token, "msg-1", timestamp=stale)
    assert not provider.verify_webhook_signature(
        body,
        headers["webhook-signature"],
        token,
        headers=headers,
    )


def test_gitlab_webhook_signing_token_requires_headers() -> None:
    provider = GitLabProvider(token="")
    token = _signing_token()
    assert not provider.verify_webhook_signature(b"{}", "v1,abc", token)


def test_verify_gitlab_signing_token_helper() -> None:
    body = b'{"test":true}'
    token = _signing_token()
    headers = _sign_gitlab_webhook(body, token, "evt-42", now=1_700_000_000.0)
    assert verify_gitlab_signing_token(
        body,
        token,
        message_id=headers["webhook-id"],
        timestamp=headers["webhook-timestamp"],
        received_signatures=headers["webhook-signature"],
        now=1_700_000_000.0,
    )


def _mr_payload(*, action: str = "open", oldrev: str | None = None) -> dict:
    payload: dict = {
        "object_kind": "merge_request",
        "project": {"path_with_namespace": "acme/backend"},
        "object_attributes": {
            "id": 93,
            "iid": 16,
            "action": action,
            "title": "Add validation",
            "draft": False,
            "work_in_progress": False,
            "last_commit": {"id": "abc123" * 5 + "ab"},
        },
    }
    if oldrev:
        payload["object_attributes"]["oldrev"] = oldrev
    return payload


def test_gitlab_parse_webhook_open() -> None:
    provider = GitLabProvider(token="")
    body = json.dumps(_mr_payload(action="open")).encode()
    event = provider.parse_webhook({"X-Gitlab-Event-UUID": "evt-1"}, body)
    assert event is not None
    assert event.repo_full_name == "acme/backend"
    assert event.pr_number == 16
    assert event.head_sha == "abc123" * 5 + "ab"
    assert event.delivery_id == "evt-1"


def test_gitlab_parse_webhook_prefers_webhook_id() -> None:
    provider = GitLabProvider(token="")
    body = json.dumps(_mr_payload(action="open")).encode()
    event = provider.parse_webhook(
        {
            "webhook-id": "wh_abc123",
            "X-Gitlab-Event-UUID": "evt-legacy",
        },
        body,
    )
    assert event is not None
    assert event.delivery_id == "wh_abc123"


def test_gitlab_parse_webhook_update_with_oldrev() -> None:
    provider = GitLabProvider(token="")
    body = json.dumps(_mr_payload(action="update", oldrev="deadbeef")).encode()
    event = provider.parse_webhook({}, body)
    assert event is not None
    assert event.action == "update"


def test_gitlab_parse_webhook_ignores_metadata_update() -> None:
    provider = GitLabProvider(token="")
    body = json.dumps(_mr_payload(action="update")).encode()
    assert provider.parse_webhook({}, body) is None


def test_gitlab_parse_webhook_ignores_merge() -> None:
    provider = GitLabProvider(token="")
    body = json.dumps(_mr_payload(action="merge")).encode()
    assert provider.parse_webhook({}, body) is None


def test_gitlab_clone_url_self_hosted() -> None:
    provider = GitLabProvider(
        token="glpat-test",
        base_url="https://gitlab.example.com",
    )
    access = provider._remote_access("acme/backend")
    assert access.clone_url == (
        "https://oauth2:glpat-test@gitlab.example.com/acme/backend.git"
    )


def test_gitlab_discussion_payload_right_side() -> None:
    provider = GitLabProvider(token="")
    refs = GitLabDiffRefs(base_sha="base", head_sha="head", start_sha="start")
    comment = InlineComment(path="src/main.py", line=10, body="issue", side="RIGHT")
    payload = provider._discussion_payload(comment, refs, body="")
    assert payload["position"]["new_line"] == 10
    assert "old_line" not in payload["position"]


def test_gitlab_discussion_payload_left_side() -> None:
    provider = GitLabProvider(token="")
    refs = GitLabDiffRefs(base_sha="base", head_sha="head", start_sha="start")
    comment = InlineComment(path="src/main.py", line=5, body="issue", side="LEFT")
    payload = provider._discussion_payload(comment, refs, body="")
    assert payload["position"]["old_line"] == 5
    assert "new_line" not in payload["position"]


@pytest.mark.asyncio
async def test_gitlab_get_pr_metadata() -> None:
    provider = GitLabProvider(token="token", base_url="https://gitlab.example.com")
    mr_response = MagicMock()
    mr_response.raise_for_status = MagicMock()
    mr_response.json.return_value = {
        "title": "Fix bug",
        "author": {"username": "dev1"},
        "source_branch": "feature",
        "target_branch": "main",
        "web_url": "https://gitlab.example.com/acme/backend/-/merge_requests/16",
        "diff_refs": {
            "base_sha": "base123",
            "head_sha": "head123",
            "start_sha": "start123",
        },
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mr_response
        mock_client_cls.return_value = mock_client

        metadata = await provider.get_pr_metadata("acme/backend", 16)

    assert metadata.title == "Fix bug"
    assert metadata.author == "dev1"
    assert metadata.head_sha == "head123"
    assert metadata.base_sha == "base123"
    mock_client.get.assert_called_once()
    called_url = mock_client.get.call_args.args[0]
    assert called_url.startswith("https://gitlab.example.com/api/v4/projects/")


@pytest.mark.asyncio
async def test_gitlab_post_inline_comments_skips_on_error() -> None:
    provider = GitLabProvider(token="token")
    refs_response = MagicMock()
    refs_response.raise_for_status = MagicMock()
    refs_response.json.return_value = {
        "diff_refs": {
            "base_sha": "base123",
            "head_sha": "head123",
            "start_sha": "start123",
        },
    }
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.text = "bad position"
    http_error = httpx.HTTPStatusError(
        "bad",
        request=MagicMock(),
        response=error_response,
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = refs_response
        mock_client.post.side_effect = http_error
        mock_client_cls.return_value = mock_client

        comments = [InlineComment(path="a.py", line=1, body="note")]
        result = await provider.post_inline_comments(
            "acme/backend",
            16,
            "head123",
            comments,
        )

    assert result.posted == ()
    assert len(result.skipped) == 1


def test_gitlab_build_pr_url() -> None:
    provider = GitLabProvider(token="")
    assert provider.build_pr_url("acme/backend", 16) == (
        "https://gitlab.com/acme/backend/-/merge_requests/16"
    )


def test_gitlab_build_pr_url_self_hosted() -> None:
    provider = GitLabProvider(
        token="",
        base_url="https://gitlab.example.com",
    )
    assert provider.build_pr_url("acme/backend", 16) == (
        "https://gitlab.example.com/acme/backend/-/merge_requests/16"
    )


def test_gitlab_build_blob_url() -> None:
    provider = GitLabProvider(token="")
    assert provider.build_blob_url("acme/backend", "abc123", "src/main.py", 10) == (
        "https://gitlab.com/acme/backend/-/blob/abc123/src/main.py#L10"
    )
    assert provider.build_blob_url("acme/backend", "abc123", "") is None


def test_gitlab_parse_webhook_includes_pr_url_from_payload() -> None:
    provider = GitLabProvider(token="")
    payload = _mr_payload(action="open")
    payload["object_attributes"]["url"] = (
        "https://gitlab.com/acme/backend/-/merge_requests/16"
    )
    body = json.dumps(payload).encode()
    event = provider.parse_webhook({}, body)
    assert event is not None
    assert event.pr_url == "https://gitlab.com/acme/backend/-/merge_requests/16"


def test_gitlab_parse_webhook_builds_pr_url_when_missing() -> None:
    provider = GitLabProvider(token="")
    body = json.dumps(_mr_payload(action="open")).encode()
    event = provider.parse_webhook({}, body)
    assert event is not None
    assert event.pr_url == ("https://gitlab.com/acme/backend/-/merge_requests/16")
