import ipaddress
import logging
import socket
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import get_code_review_settings
from app.repositories.identity_providers import (
    IdentityProviderRepository,
    IdentityProviderRow,
)
from app.repositories.organizations import DEFAULT_ORG_ID, OrganizationRepository
from app.schemas.identity_provider import (
    IdentityProviderPublicResponse,
    IdentityProviderResponse,
    IdentityProviderUpsert,
    default_display_name,
    normalize_saml_cert,
    resolve_oidc_issuer,
)
from app.services.secrets import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


def oidc_redirect_uri() -> str:
    base = get_code_review_settings().frontend_url.rstrip("/")
    return f"{base}/api/v1/auth/callback"


def saml_acs_url() -> str:
    base = get_code_review_settings().frontend_url.rstrip("/")
    return f"{base}/api/v1/auth/saml/acs"


def saml_metadata_url() -> str:
    base = get_code_review_settings().frontend_url.rstrip("/")
    return f"{base}/api/v1/auth/saml/metadata"


def saml_sp_entity_id() -> str:
    base = get_code_review_settings().frontend_url.rstrip("/")
    return f"{base}/api/v1/auth/saml/metadata"


def to_identity_provider_response(row: IdentityProviderRow) -> IdentityProviderResponse:
    return IdentityProviderResponse(
        organization_id=row.organization_id,
        protocol=row.protocol,
        preset=row.preset,
        enabled=row.enabled,
        display_name=row.display_name,
        oidc_issuer=row.oidc_issuer,
        oidc_client_id=row.oidc_client_id,
        oidc_client_secret_configured=bool(row.oidc_client_secret_encrypted),
        oidc_scopes=row.oidc_scopes,
        oidc_authorize_url=row.oidc_authorize_url,
        oidc_token_url=row.oidc_token_url,
        oidc_userinfo_url=row.oidc_userinfo_url,
        saml_idp_entity_id=row.saml_idp_entity_id,
        saml_idp_sso_url=row.saml_idp_sso_url,
        saml_idp_slo_url=row.saml_idp_slo_url,
        saml_idp_cert_configured=bool(row.saml_idp_cert),
        saml_sp_entity_id=row.saml_sp_entity_id,
        saml_sp_acs_url=row.saml_sp_acs_url,
        saml_sp_cert_configured=bool(row.saml_sp_cert),
        saml_sp_private_key_configured=bool(row.saml_sp_private_key_encrypted),
        email_claim=row.email_claim,
        name_claim=row.name_claim,
        sub_claim=row.sub_claim,
        oidc_redirect_uri=oidc_redirect_uri(),
        saml_metadata_url=saml_metadata_url(),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_public_response(
    row: IdentityProviderRow | None,
) -> IdentityProviderPublicResponse:
    if row is None or not row.enabled:
        return IdentityProviderPublicResponse(
            enabled=False,
            display_name="",
            protocol="",
        )
    return IdentityProviderPublicResponse(
        enabled=True,
        display_name=row.display_name,
        protocol=row.protocol,
    )


async def get_identity_provider(conn) -> IdentityProviderResponse | None:
    org = await OrganizationRepository(conn).get_default()
    org_id = org.id if org else DEFAULT_ORG_ID
    row = await IdentityProviderRepository(conn).get(org_id)
    if row is None:
        return None
    return to_identity_provider_response(row)


async def get_enabled_identity_provider(conn) -> IdentityProviderRow | None:
    return await IdentityProviderRepository(conn).get_enabled()


async def get_public_identity_provider(conn) -> IdentityProviderPublicResponse:
    row = await IdentityProviderRepository(conn).get_enabled()
    return to_public_response(row)


async def upsert_identity_provider(
    conn,
    payload: IdentityProviderUpsert,
) -> IdentityProviderResponse:
    org = await OrganizationRepository(conn).get_default()
    if org is None:
        msg = "organization not configured"
        raise ValueError(msg)

    display_name = payload.display_name.strip() or default_display_name(
        payload.preset,
        payload.protocol,
    )

    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_secret_encrypted: str | None = None
    clear_oidc_secret = payload.clear_oidc_client_secret

    saml_idp_entity_id = payload.saml_idp_entity_id
    saml_idp_sso_url = payload.saml_idp_sso_url
    saml_idp_slo_url = payload.saml_idp_slo_url
    saml_idp_cert = payload.saml_idp_cert
    sp_entity_id = saml_sp_entity_id()
    sp_acs = saml_acs_url()
    sp_cert: str | None = None
    sp_key_encrypted: str | None = None

    if payload.protocol == "oidc":
        oidc_issuer = resolve_oidc_issuer(payload)
        oidc_client_id = (payload.oidc_client_id or "").strip() or None
        if payload.oidc_client_secret:
            oidc_secret_encrypted = encrypt_secret(payload.oidc_client_secret)
        if not oidc_client_id:
            msg = "client_id required for OIDC"
            raise ValueError(msg)
        existing = await IdentityProviderRepository(conn).get(org.id)
        if (
            existing is None
            and not oidc_secret_encrypted
            and not payload.clear_oidc_client_secret
        ):
            msg = "client_secret required for OIDC"
            raise ValueError(msg)
    else:
        if payload.saml_idp_metadata_url or payload.saml_idp_metadata_xml:
            parsed = await _parse_saml_idp_metadata(
                url=payload.saml_idp_metadata_url,
                xml=payload.saml_idp_metadata_xml,
            )
            saml_idp_entity_id = parsed.get("entity_id") or saml_idp_entity_id
            saml_idp_sso_url = parsed.get("sso_url") or saml_idp_sso_url
            saml_idp_slo_url = parsed.get("slo_url") or saml_idp_slo_url
            saml_idp_cert = parsed.get("cert") or saml_idp_cert
        if saml_idp_cert:
            saml_idp_cert = normalize_saml_cert(saml_idp_cert)
        if not saml_idp_entity_id or not saml_idp_sso_url or not saml_idp_cert:
            msg = "SAML IdP entity_id, SSO URL, and certificate are required"
            raise ValueError(msg)

        existing = await IdentityProviderRepository(conn).get(org.id)
        if existing is None or not existing.saml_sp_cert:
            sp_cert, sp_private_key = generate_sp_certificate()
            sp_key_encrypted = encrypt_secret(sp_private_key)
        else:
            sp_cert = existing.saml_sp_cert

    row = await IdentityProviderRepository(conn).upsert(
        organization_id=org.id,
        protocol=payload.protocol,
        preset=payload.preset,
        enabled=payload.enabled,
        display_name=display_name,
        oidc_issuer=oidc_issuer,
        oidc_client_id=oidc_client_id,
        oidc_client_secret_encrypted=oidc_secret_encrypted,
        oidc_scopes=payload.oidc_scopes,
        oidc_authorize_url=(payload.oidc_authorize_url or "").strip() or None,
        oidc_token_url=(payload.oidc_token_url or "").strip() or None,
        oidc_userinfo_url=(payload.oidc_userinfo_url or "").strip() or None,
        saml_idp_entity_id=saml_idp_entity_id,
        saml_idp_sso_url=saml_idp_sso_url,
        saml_idp_slo_url=saml_idp_slo_url,
        saml_idp_cert=saml_idp_cert,
        saml_sp_entity_id=sp_entity_id,
        saml_sp_acs_url=sp_acs,
        saml_sp_cert=sp_cert,
        saml_sp_private_key_encrypted=sp_key_encrypted,
        email_claim=payload.email_claim,
        name_claim=payload.name_claim,
        sub_claim=payload.sub_claim,
        clear_oidc_client_secret=clear_oidc_secret,
    )
    logger.info(
        "Updated identity provider protocol=%s preset=%s",
        row.protocol,
        row.preset,
    )
    return to_identity_provider_response(row)


async def delete_identity_provider(conn) -> None:
    org = await OrganizationRepository(conn).get_default()
    if org is None:
        return
    await IdentityProviderRepository(conn).delete(org.id)


async def upload_saml_sp_cert(
    conn,
    *,
    sp_cert: str,
    sp_private_key: str,
) -> IdentityProviderResponse:
    org = await OrganizationRepository(conn).get_default()
    if org is None:
        msg = "organization not configured"
        raise ValueError(msg)
    existing = await IdentityProviderRepository(conn).get(org.id)
    if existing is None or existing.protocol != "saml":
        msg = "SAML identity provider not configured"
        raise ValueError(msg)
    row = await IdentityProviderRepository(conn).upsert(
        organization_id=org.id,
        protocol=existing.protocol,
        preset=existing.preset,
        enabled=existing.enabled,
        display_name=existing.display_name,
        saml_sp_cert=normalize_saml_cert(sp_cert),
        saml_sp_private_key_encrypted=encrypt_secret(sp_private_key.strip()),
        saml_sp_entity_id=existing.saml_sp_entity_id or saml_sp_entity_id(),
        saml_sp_acs_url=existing.saml_sp_acs_url or saml_acs_url(),
        email_claim=existing.email_claim,
        name_claim=existing.name_claim,
        sub_claim=existing.sub_claim,
    )
    return to_identity_provider_response(row)


def get_oidc_client_secret(row: IdentityProviderRow) -> str:
    if not row.oidc_client_secret_encrypted:
        return ""
    return decrypt_secret(row.oidc_client_secret_encrypted)


def get_saml_sp_private_key(row: IdentityProviderRow) -> str:
    if not row.saml_sp_private_key_encrypted:
        return ""
    return decrypt_secret(row.saml_sp_private_key_encrypted)


def generate_sp_certificate() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "cogito-review-sp"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    cert_body = normalize_saml_cert(cert_pem)
    return cert_body, key_pem


async def _parse_saml_idp_metadata(
    *,
    url: str | None,
    xml: str | None,
) -> dict[str, str]:
    from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

    if url:
        _validate_metadata_url(url.strip())
        idp_data = OneLogin_Saml2_IdPMetadataParser.parse_remote(
            url.strip(),
            timeout=10,
        )
    elif xml:
        idp_data = OneLogin_Saml2_IdPMetadataParser.parse(xml)
    else:
        return {}

    idp = idp_data.get("idp", {})
    entity_id = idp.get("entityId", "")
    sso_url = _extract_binding_url(idp.get("singleSignOnService", {}))
    slo_url = _extract_binding_url(idp.get("singleLogoutService", {}))
    cert = idp.get("x509cert", "")
    return {
        "entity_id": entity_id,
        "sso_url": sso_url,
        "slo_url": slo_url,
        "cert": cert,
    }


def _extract_binding_url(services: dict | list) -> str:
    if isinstance(services, dict):
        return services.get("url", "")
    if isinstance(services, list):
        for service in services:
            binding = service.get("Binding", "")
            if "HTTP-Redirect" in binding or "HTTP-POST" in binding:
                return service.get("url", service.get("Location", ""))
        if services:
            first = services[0]
            return first.get("url", first.get("Location", ""))
    return ""


def _validate_metadata_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        msg = "metadata URL must use HTTPS"
        raise ValueError(msg)
    host = parsed.hostname
    if not host:
        msg = "invalid metadata URL"
        raise ValueError(msg)
    try:
        infos = socket.getaddrinfo(host, parsed.port or 443)
    except socket.gaierror as exc:
        msg = "metadata URL host could not be resolved"
        raise ValueError(msg) from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            msg = "metadata URL must not resolve to a private address"
            raise ValueError(msg)


async def provision_user_from_claims(
    conn,
    *,
    protocol: str,
    issuer: str,
    claims: dict,
    email_claim: str,
    name_claim: str,
    sub_claim: str,
) -> tuple:
    from app.repositories.users import UserRepository
    from app.schemas.identity_provider import build_external_subject

    settings = get_code_review_settings()
    sub = str(claims.get(sub_claim) or claims.get("sub") or "")
    email = str(claims.get(email_claim) or claims.get("email") or "")
    name = str(claims.get(name_claim) or claims.get("name") or "")
    if not sub or not email:
        msg = "missing required identity claims"
        raise ValueError(msg)

    external_id = build_external_subject(protocol=protocol, issuer=issuer, sub=sub)
    user_repo = UserRepository(conn)
    existing = await user_repo.get_by_oidc_sub(external_id)
    is_org_admin = False
    if existing is None:
        admin_count = await user_repo.count_org_admins()
        bootstrap_email = settings.bootstrap_org_admin_email.strip().lower()
        if admin_count == 0 or (
            bootstrap_email and email.strip().lower() == bootstrap_email
        ):
            is_org_admin = True

    user = await user_repo.upsert_external_user(
        external_id=external_id,
        email=email,
        name=name or email,
        is_org_admin=is_org_admin if existing is None else existing.is_org_admin,
    )
    return user


def extract_nested_claim(claims: dict, claim_path: str) -> str:
    if not claim_path:
        return ""
    parts = claim_path.split(".")
    current: object = claims
    for part in parts:
        if not isinstance(current, dict):
            return ""
        current = current.get(part, "")
    return str(current) if current else ""
