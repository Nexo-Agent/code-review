from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.auth.oidc import _get_server_metadata, build_authorization_url
from app.repositories.identity_providers import IdentityProviderRow


def _idp_row(**overrides: object) -> IdentityProviderRow:
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "enabled": True,
        "protocol": "oidc",
        "preset": "google",
        "display_name": "Google",
        "oidc_issuer": "https://accounts.google.com",
        "oidc_client_id": "client-id",
        "oidc_client_secret_encrypted": "enc",
        "oidc_scopes": "openid email profile",
        "oidc_authorize_url": None,
        "oidc_token_url": None,
        "oidc_userinfo_url": None,
        "saml_idp_entity_id": None,
        "saml_idp_sso_url": None,
        "saml_idp_slo_url": None,
        "saml_idp_cert": None,
        "saml_sp_entity_id": None,
        "saml_sp_acs_url": None,
        "saml_sp_cert": None,
        "saml_sp_private_key_encrypted": None,
        "email_claim": "email",
        "name_claim": "name",
        "sub_claim": "sub",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return IdentityProviderRow(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_server_metadata_from_discovery() -> None:
    client = AsyncMock()
    response = MagicMock()
    response.json.return_value = {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
    }
    client.request = AsyncMock(return_value=response)

    row = _idp_row()
    metadata = await _get_server_metadata(client, row)

    assert "authorization_endpoint" in metadata
    client.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_authorization_url_uses_discovery() -> None:
    row = _idp_row()
    with (
        patch(
            "app.auth.oidc.build_oauth_client",
            new_callable=AsyncMock,
        ) as build_client,
        patch(
            "app.auth.oidc._get_server_metadata",
            new_callable=AsyncMock,
        ) as get_metadata,
        patch(
            "app.services.identity_provider.oidc_redirect_uri",
            return_value="http://localhost/callback",
        ),
    ):
        client = MagicMock()
        client.create_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?state=abc",
            "abc",
        )
        build_client.return_value = client
        get_metadata.return_value = {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        }

        url = await build_authorization_url(row=row, state="state-token")

    assert url.startswith("https://accounts.google.com")
    client.create_authorization_url.assert_called_once()
