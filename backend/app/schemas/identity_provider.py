import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PROTOCOLS = ("oidc", "saml")
PRESETS = ("google", "okta", "keycloak", "entra", "auth0", "custom")


class IdentityProviderPublicResponse(BaseModel):
    enabled: bool
    display_name: str
    protocol: str


class IdentityProviderResponse(BaseModel):
    organization_id: UUID
    protocol: str
    preset: str
    enabled: bool
    display_name: str
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret_configured: bool = False
    oidc_scopes: str = "openid email profile"
    oidc_authorize_url: str | None = None
    oidc_token_url: str | None = None
    oidc_userinfo_url: str | None = None
    saml_idp_entity_id: str | None = None
    saml_idp_sso_url: str | None = None
    saml_idp_slo_url: str | None = None
    saml_idp_cert_configured: bool = False
    saml_sp_entity_id: str | None = None
    saml_sp_acs_url: str | None = None
    saml_sp_cert_configured: bool = False
    saml_sp_private_key_configured: bool = False
    email_claim: str = "email"
    name_claim: str = "name"
    sub_claim: str = "sub"
    oidc_redirect_uri: str
    saml_metadata_url: str
    created_at: datetime
    updated_at: datetime


class IdentityProviderUpsert(BaseModel):
    protocol: str = Field(pattern="^(oidc|saml)$")
    preset: str = Field(pattern="^(google|okta|keycloak|entra|auth0|custom)$")
    enabled: bool = False
    display_name: str = Field(default="", max_length=128)
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    clear_oidc_client_secret: bool = False
    oidc_scopes: str = Field(default="openid email profile", max_length=256)
    oidc_authorize_url: str | None = None
    oidc_token_url: str | None = None
    oidc_userinfo_url: str | None = None
    saml_idp_metadata_url: str | None = None
    saml_idp_metadata_xml: str | None = None
    saml_idp_entity_id: str | None = None
    saml_idp_sso_url: str | None = None
    saml_idp_slo_url: str | None = None
    saml_idp_cert: str | None = None
    email_claim: str = Field(default="email", max_length=128)
    name_claim: str = Field(default="name", max_length=128)
    sub_claim: str = Field(default="sub", max_length=128)
    preset_tenant_id: str | None = Field(default=None, max_length=256)
    preset_domain: str | None = Field(default=None, max_length=256)
    preset_base_url: str | None = Field(default=None, max_length=512)
    preset_realm: str | None = Field(default=None, max_length=256)

    @field_validator("preset_domain", "preset_base_url")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SamlSpCertUpload(BaseModel):
    sp_cert: str = Field(min_length=1)
    sp_private_key: str = Field(min_length=1)


def build_external_subject(*, protocol: str, issuer: str, sub: str) -> str:
    normalized_issuer = issuer.strip().rstrip("/")
    normalized_sub = sub.strip()
    return f"{protocol}:{normalized_issuer}:{normalized_sub}"


def resolve_oidc_issuer(payload: IdentityProviderUpsert) -> str:
    preset = payload.preset
    if preset == "google":
        return "https://accounts.google.com"
    if preset == "entra":
        tenant = (payload.preset_tenant_id or "").strip()
        if not tenant:
            msg = "tenant_id required for Entra ID preset"
            raise ValueError(msg)
        return f"https://login.microsoftonline.com/{tenant}/v2.0"
    if preset == "okta":
        domain = (payload.preset_domain or "").strip().removesuffix("/")
        if not domain:
            msg = "domain required for Okta preset"
            raise ValueError(msg)
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return domain
    if preset == "keycloak":
        base = (payload.preset_base_url or "").strip().removesuffix("/")
        realm = (payload.preset_realm or "").strip()
        if not base or not realm:
            msg = "base_url and realm required for Keycloak preset"
            raise ValueError(msg)
        if not base.startswith("http"):
            base = f"https://{base}"
        return f"{base}/realms/{realm}"
    if preset == "auth0":
        domain = (payload.preset_domain or "").strip().removesuffix("/")
        if not domain:
            msg = "domain required for Auth0 preset"
            raise ValueError(msg)
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return domain
    issuer = (payload.oidc_issuer or "").strip()
    if not issuer:
        msg = "issuer required for custom OIDC preset"
        raise ValueError(msg)
    return issuer


def default_display_name(preset: str, protocol: str) -> str:
    labels = {
        "google": "Google Workspace",
        "entra": "Microsoft Entra ID",
        "okta": "Okta",
        "keycloak": "Keycloak",
        "auth0": "Auth0",
        "custom": "SSO",
    }
    if protocol == "saml":
        return labels.get(preset, "SAML SSO")
    return labels.get(preset, "SSO")


def normalize_saml_cert(cert: str) -> str:
    body = cert.strip()
    body = re.sub(r"-----BEGIN CERTIFICATE-----", "", body)
    body = re.sub(r"-----END CERTIFICATE-----", "", body)
    return body.replace("\n", "").replace("\r", "").strip()
