from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oidc.discovery import get_well_known_url

from app.repositories.identity_providers import IdentityProviderRow
from app.services.identity_provider import get_oidc_client_secret, oidc_redirect_uri


async def build_oauth_client(row: IdentityProviderRow) -> AsyncOAuth2Client:
    if not row.oidc_issuer or not row.oidc_client_id:
        msg = "OIDC identity provider is not configured"
        raise RuntimeError(msg)
    client_secret = get_oidc_client_secret(row)
    metadata_url = get_well_known_url(row.oidc_issuer, external=True)
    return AsyncOAuth2Client(
        client_id=row.oidc_client_id,
        client_secret=client_secret,
        scope=row.oidc_scopes,
        server_metadata_url=metadata_url,
    )


async def _fetch_oidc_discovery(
    client: AsyncOAuth2Client,
    issuer: str,
) -> dict:
    metadata_url = get_well_known_url(issuer, external=True)
    response = await client.request("GET", metadata_url, withhold_token=True)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        msg = "Unexpected OIDC discovery response type"
        raise RuntimeError(msg)
    return data


async def _get_server_metadata(
    client: AsyncOAuth2Client,
    row: IdentityProviderRow,
) -> dict:
    if row.oidc_authorize_url and row.oidc_token_url:
        metadata = {
            "authorization_endpoint": row.oidc_authorize_url,
            "token_endpoint": row.oidc_token_url,
        }
        if row.oidc_userinfo_url:
            metadata["userinfo_endpoint"] = row.oidc_userinfo_url
        return metadata

    if not row.oidc_issuer:
        msg = "OIDC issuer is not configured"
        raise RuntimeError(msg)
    return await _fetch_oidc_discovery(client, row.oidc_issuer)


async def build_authorization_url(*, row: IdentityProviderRow, state: str) -> str:
    client = await build_oauth_client(row)
    metadata = await _get_server_metadata(client, row)
    uri, _ = client.create_authorization_url(
        metadata["authorization_endpoint"],
        redirect_uri=oidc_redirect_uri(),
        state=state,
    )
    return uri


async def exchange_code(*, row: IdentityProviderRow, code: str) -> dict[str, str]:
    client = await build_oauth_client(row)
    metadata = await _get_server_metadata(client, row)
    await client.fetch_token(
        metadata["token_endpoint"],
        code=code,
        redirect_uri=oidc_redirect_uri(),
    )

    userinfo_endpoint = row.oidc_userinfo_url or metadata.get("userinfo_endpoint")
    if not userinfo_endpoint:
        msg = "OIDC provider metadata missing userinfo_endpoint"
        raise RuntimeError(msg)

    response = await client.get(userinfo_endpoint)
    response.raise_for_status()
    userinfo = response.json()
    if not isinstance(userinfo, dict):
        msg = "Unexpected userinfo response type"
        raise RuntimeError(msg)
    return userinfo
