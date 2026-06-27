import pytest

from app.schemas.identity_provider import (
    IdentityProviderUpsert,
    build_external_subject,
    resolve_oidc_issuer,
)


def test_build_external_subject() -> None:
    subject = build_external_subject(
        protocol="oidc",
        issuer="https://accounts.google.com",
        sub="user-123",
    )
    assert subject == "oidc:https://accounts.google.com:user-123"


def test_resolve_google_issuer() -> None:
    payload = IdentityProviderUpsert(protocol="oidc", preset="google")
    assert resolve_oidc_issuer(payload) == "https://accounts.google.com"


def test_resolve_entra_issuer() -> None:
    payload = IdentityProviderUpsert(
        protocol="oidc",
        preset="entra",
        preset_tenant_id="tenant-guid",
    )
    assert (
        resolve_oidc_issuer(payload)
        == "https://login.microsoftonline.com/tenant-guid/v2.0"
    )


def test_resolve_custom_requires_issuer() -> None:
    payload = IdentityProviderUpsert(protocol="oidc", preset="custom")
    with pytest.raises(ValueError, match="issuer required"):
        resolve_oidc_issuer(payload)
