from fastapi import Request

from app.repositories.identity_providers import IdentityProviderRow
from app.services.identity_provider import get_saml_sp_private_key


def prepare_fastapi_request(request: Request, post_data: dict | None = None) -> dict:
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    https = "on" if forwarded_proto == "https" else "off"
    return {
        "https": https,
        "http_host": request.url.hostname or "localhost",
        "script_name": request.url.path,
        "server_port": str(request.url.port or (443 if https == "on" else 80)),
        "get_data": dict(request.query_params),
        "post_data": post_data or {},
    }


def build_saml_settings(row: IdentityProviderRow) -> dict:
    sp_private_key = get_saml_sp_private_key(row)
    if not row.saml_sp_cert or not sp_private_key:
        msg = "SAML service provider certificate is not configured"
        raise RuntimeError(msg)
    if not row.saml_idp_entity_id or not row.saml_idp_sso_url or not row.saml_idp_cert:
        msg = "SAML identity provider is not configured"
        raise RuntimeError(msg)

    return {
        "strict": True,
        "debug": False,
        "lowercase_urlencoding": True,
        "sp": {
            "entityId": row.saml_sp_entity_id or "",
            "assertionConsumerService": {
                "url": row.saml_sp_acs_url or "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "x509cert": row.saml_sp_cert,
            "privateKey": sp_private_key,
        },
        "idp": {
            "entityId": row.saml_idp_entity_id,
            "singleSignOnService": {
                "url": row.saml_idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": row.saml_idp_cert,
        },
        "security": {
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
        },
    }


def build_saml_auth(
    request: Request,
    row: IdentityProviderRow,
    post_data: dict | None = None,
):
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    settings = build_saml_settings(row)
    req = prepare_fastapi_request(request, post_data)
    return OneLogin_Saml2_Auth(req, settings)


def process_acs_response(auth) -> dict[str, str]:
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        reason = auth.get_last_error_reason()
        msg = f"SAML authentication failed: {', '.join(errors)} ({reason})"
        raise RuntimeError(msg)
    if not auth.is_authenticated():
        msg = "SAML authentication failed"
        raise RuntimeError(msg)

    attributes = auth.get_attributes()
    name_id = auth.get_nameid() or ""
    claims: dict[str, str] = {"sub": name_id}
    for key, values in attributes.items():
        if values:
            claims[key] = values[0] if isinstance(values, list) else str(values)

    email_keys = (
        "email",
        "mail",
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    )
    name_keys = (
        "name",
        "displayName",
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    )
    for key in email_keys:
        if key in claims and claims[key]:
            claims.setdefault("email", claims[key])
            break
    for key in name_keys:
        if key in claims and claims[key]:
            claims.setdefault("name", claims[key])
            break
    if "email" not in claims and "@" in name_id:
        claims["email"] = name_id
    return claims


def get_sp_metadata(row: IdentityProviderRow) -> str:
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    settings = build_saml_settings(row)
    saml_settings = OneLogin_Saml2_Settings(settings=settings, sp_validation_only=True)
    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)
    if errors:
        msg = f"Invalid SP metadata: {', '.join(errors)}"
        raise RuntimeError(msg)
    return metadata
