from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import AuthContext, get_auth_context, get_current_user
from app.dependencies import get_conn
from app.main import create_app
from app.repositories.organizations import DEFAULT_ORG_ID
from tests.conftest import make_dev_user


@pytest.fixture
async def app_client():
    app = create_app()
    mock_conn = AsyncMock()

    async def override_get_conn():
        yield mock_conn

    app.dependency_overrides[get_conn] = override_get_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, client, mock_conn
    app.dependency_overrides.clear()


def _set_auth(app, *, user, auth_enabled: bool = True) -> None:
    async def override_auth_context():
        return AuthContext(
            user=user,
            accessible_team_ids=[],
            auth_enabled=auth_enabled,
        )

    async def override_current_user():
        return user

    app.dependency_overrides[get_auth_context] = override_auth_context
    app.dependency_overrides[get_current_user] = override_current_user


@pytest.mark.asyncio
async def test_get_identity_provider_requires_org_admin(app_client) -> None:
    app, client, _mock_conn = app_client
    member = make_dev_user(is_org_admin=False)
    _set_auth(app, user=member)

    response = await client.get("/api/v1/settings/identity-provider")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_put_identity_provider_oidc(app_client) -> None:
    app, client, _mock_conn = app_client
    admin = make_dev_user(is_org_admin=True)
    _set_auth(app, user=admin)

    with patch(
        "app.api.v1.identity_provider.upsert_identity_provider",
        new_callable=AsyncMock,
    ) as upsert:
        upsert.return_value = {
            "organization_id": str(DEFAULT_ORG_ID),
            "protocol": "oidc",
            "preset": "google",
            "enabled": True,
            "display_name": "Google Workspace",
            "oidc_issuer": "https://accounts.google.com",
            "oidc_client_id": "client-id",
            "oidc_client_secret_configured": True,
            "oidc_scopes": "openid email profile",
            "oidc_authorize_url": None,
            "oidc_token_url": None,
            "oidc_userinfo_url": None,
            "saml_idp_entity_id": None,
            "saml_idp_sso_url": None,
            "saml_idp_slo_url": None,
            "saml_idp_cert_configured": False,
            "saml_sp_entity_id": None,
            "saml_sp_acs_url": None,
            "saml_sp_cert_configured": False,
            "saml_sp_private_key_configured": False,
            "email_claim": "email",
            "name_claim": "name",
            "sub_claim": "sub",
            "oidc_redirect_uri": "http://localhost:5173/api/v1/auth/callback",
            "saml_metadata_url": "http://localhost:5173/api/v1/auth/saml/metadata",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        response = await client.put(
            "/api/v1/settings/identity-provider",
            json={
                "protocol": "oidc",
                "preset": "google",
                "enabled": True,
                "oidc_client_id": "client-id",
                "oidc_client_secret": "secret",
            },
        )

    assert response.status_code == 200
    assert response.json()["preset"] == "google"


@pytest.mark.asyncio
async def test_get_public_idp_when_disabled(app_client) -> None:
    app, client, _mock_conn = app_client

    with patch(
        "app.api.v1.auth.get_public_identity_provider",
        new_callable=AsyncMock,
    ) as get_public:
        get_public.return_value = {
            "enabled": False,
            "display_name": "",
            "protocol": "",
        }
        response = await client.get("/api/v1/auth/idp")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
