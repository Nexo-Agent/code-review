import base64
import json

from coreview_shared.git.bitbucket_dc import (
    BitbucketDataCenterProvider,
    parse_repo_full_name,
)


def _dc_payload() -> dict:
    return {
        "pullRequest": {
            "id": 7,
            "title": "Feature branch",
            "state": "OPEN",
            "fromRef": {
                "latestCommit": "abc123" * 5 + "ab",
            },
            "toRef": {
                "repository": {
                    "slug": "backend",
                    "project": {"key": "ACME"},
                },
            },
            "links": {"self": [{"href": "https://bitbucket.example.com/pull/7"}]},
        },
    }


def test_parse_repo_full_name_valid() -> None:
    assert parse_repo_full_name("ACME/backend") == ("ACME", "backend")


def test_bitbucket_dc_webhook_basic_auth_valid() -> None:
    provider = BitbucketDataCenterProvider(
        token="",
        base_url="https://bitbucket.example.com",
    )
    creds = base64.b64encode(b"hook-user:hook-pass").decode()
    assert provider.verify_webhook_signature(
        b"{}",
        f"Basic {creds}",
        "hook-user:hook-pass",
    )


def test_bitbucket_dc_webhook_basic_auth_invalid() -> None:
    provider = BitbucketDataCenterProvider(
        token="",
        base_url="https://bitbucket.example.com",
    )
    assert not provider.verify_webhook_signature(
        b"{}",
        "Basic bad",
        "hook-user:hook-pass",
    )


def test_bitbucket_dc_parse_webhook_opened() -> None:
    provider = BitbucketDataCenterProvider(
        token="",
        base_url="https://bitbucket.example.com",
    )
    body = json.dumps(_dc_payload()).encode()
    event = provider.parse_webhook({"X-Event-Key": "pr:opened"}, body)
    assert event is not None
    assert event.repo_full_name == "ACME/backend"
    assert event.pr_number == 7
    assert event.head_sha == "abc123" * 5 + "ab"


def test_bitbucket_dc_parse_webhook_ignores_declined() -> None:
    provider = BitbucketDataCenterProvider(
        token="",
        base_url="https://bitbucket.example.com",
    )
    payload = _dc_payload()
    payload["pullRequest"]["state"] = "DECLINED"
    body = json.dumps(payload).encode()
    assert provider.parse_webhook({"X-Event-Key": "pr:opened"}, body) is None
