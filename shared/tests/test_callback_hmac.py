import hashlib
import hmac

from coreview_shared.auth.callback_hmac import sign_payload, verify_payload_signature


def test_sign_and_verify_payload() -> None:
    body = b'{"event":"review.started"}'
    secret = "dev-secret"
    signature = sign_payload(body, secret)
    assert signature.startswith("sha256=")
    assert verify_payload_signature(body, signature, secret)


def test_verify_payload_rejects_invalid_signature() -> None:
    body = b"{}"
    assert not verify_payload_signature(body, "sha256=deadbeef", "secret")
    assert not verify_payload_signature(body, None, "secret")
    assert not verify_payload_signature(body, "sha256=abc", "")


def test_github_hmac_matches_shared_helper() -> None:
    secret = "test-secret"
    payload = b'{"action":"opened"}'
    legacy = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_payload_signature(payload, legacy, secret)
