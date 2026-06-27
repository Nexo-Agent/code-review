import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oidc.discovery import get_well_known_url

from app.config import get_code_review_settings

_oauth_client: AsyncOAuth2Client | None = None
_server_metadata: dict | None = None


def get_oauth_client() -> AsyncOAuth2Client:
    global _oauth_client
    settings = get_code_review_settings()
    if _oauth_client is None:
        metadata_url = get_well_known_url(settings.oidc_issuer, external=True)
        _oauth_client = AsyncOAuth2Client(
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            scope="openid email profile",
            server_metadata_url=metadata_url,
        )
    return _oauth_client


async def _get_server_metadata() -> dict:
    global _server_metadata
    if _server_metadata is not None:
        return _server_metadata

    settings = get_code_review_settings()
    if settings.oidc_authorize_url and settings.oidc_token_url:
        _server_metadata = {
            "authorization_endpoint": settings.oidc_authorize_url,
            "token_endpoint": settings.oidc_token_url,
        }
        return _server_metadata

    discovery_url = get_well_known_url(settings.oidc_issuer, external=True)
    async with httpx.AsyncClient() as client:
        response = await client.get(discovery_url)
        response.raise_for_status()
        _server_metadata = response.json()
    return _server_metadata


async def build_authorization_url(*, state: str) -> str:
    settings = get_code_review_settings()
    client = get_oauth_client()
    metadata = await _get_server_metadata()
    uri, _ = client.create_authorization_url(
        settings.oidc_authorize_url or metadata["authorization_endpoint"],
        redirect_uri=settings.oidc_redirect_uri,
        state=state,
    )
    return uri


async def exchange_code(code: str) -> dict[str, str]:
    settings = get_code_review_settings()
    client = get_oauth_client()
    metadata = await _get_server_metadata()
    await client.fetch_token(
        settings.oidc_token_url or metadata["token_endpoint"],
        code=code,
        redirect_uri=settings.oidc_redirect_uri,
    )

    userinfo_endpoint = metadata.get("userinfo_endpoint")
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
