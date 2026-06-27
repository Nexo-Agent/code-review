from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

_IDP_SELECT = """
    organization_id, protocol, preset, enabled, display_name,
    oidc_issuer, oidc_client_id, oidc_client_secret_encrypted,
    oidc_scopes, oidc_authorize_url, oidc_token_url, oidc_userinfo_url,
    saml_idp_entity_id, saml_idp_sso_url, saml_idp_slo_url, saml_idp_cert,
    saml_sp_entity_id, saml_sp_acs_url, saml_sp_cert,
    saml_sp_private_key_encrypted,
    email_claim, name_claim, sub_claim,
    created_at, updated_at
"""


@dataclass(frozen=True, slots=True)
class IdentityProviderRow:
    organization_id: UUID
    protocol: str
    preset: str
    enabled: bool
    display_name: str
    oidc_issuer: str | None
    oidc_client_id: str | None
    oidc_client_secret_encrypted: str | None
    oidc_scopes: str
    oidc_authorize_url: str | None
    oidc_token_url: str | None
    oidc_userinfo_url: str | None
    saml_idp_entity_id: str | None
    saml_idp_sso_url: str | None
    saml_idp_slo_url: str | None
    saml_idp_cert: str | None
    saml_sp_entity_id: str | None
    saml_sp_acs_url: str | None
    saml_sp_cert: str | None
    saml_sp_private_key_encrypted: str | None
    email_claim: str
    name_claim: str
    sub_claim: str
    created_at: datetime
    updated_at: datetime


class IdentityProviderRepository:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, organization_id: UUID) -> IdentityProviderRow | None:
        row = await self._conn.fetchrow(
            f"""
            SELECT {_IDP_SELECT}
            FROM organization_identity_providers
            WHERE organization_id = $1
            """,
            organization_id,
        )
        return _row_to_identity_provider(row) if row else None

    async def get_enabled(self) -> IdentityProviderRow | None:
        row = await self._conn.fetchrow(
            f"""
            SELECT {_IDP_SELECT}
            FROM organization_identity_providers
            WHERE enabled = true
            LIMIT 1
            """
        )
        return _row_to_identity_provider(row) if row else None

    async def upsert(
        self,
        *,
        organization_id: UUID,
        protocol: str,
        preset: str,
        enabled: bool,
        display_name: str,
        oidc_issuer: str | None = None,
        oidc_client_id: str | None = None,
        oidc_client_secret_encrypted: str | None = None,
        oidc_scopes: str = "openid email profile",
        oidc_authorize_url: str | None = None,
        oidc_token_url: str | None = None,
        oidc_userinfo_url: str | None = None,
        saml_idp_entity_id: str | None = None,
        saml_idp_sso_url: str | None = None,
        saml_idp_slo_url: str | None = None,
        saml_idp_cert: str | None = None,
        saml_sp_entity_id: str | None = None,
        saml_sp_acs_url: str | None = None,
        saml_sp_cert: str | None = None,
        saml_sp_private_key_encrypted: str | None = None,
        email_claim: str = "email",
        name_claim: str = "name",
        sub_claim: str = "sub",
        clear_oidc_client_secret: bool = False,
        clear_saml_sp_private_key: bool = False,
    ) -> IdentityProviderRow:
        existing = await self.get(organization_id)
        secret = oidc_client_secret_encrypted
        sp_key = saml_sp_private_key_encrypted
        if existing is not None:
            if secret is None and not clear_oidc_client_secret:
                secret = existing.oidc_client_secret_encrypted
            if sp_key is None and not clear_saml_sp_private_key:
                sp_key = existing.saml_sp_private_key_encrypted
            if saml_sp_cert is None:
                saml_sp_cert = existing.saml_sp_cert
            if saml_sp_entity_id is None:
                saml_sp_entity_id = existing.saml_sp_entity_id
            if saml_sp_acs_url is None:
                saml_sp_acs_url = existing.saml_sp_acs_url

        row = await self._conn.fetchrow(
            f"""
            INSERT INTO organization_identity_providers (
                organization_id, protocol, preset, enabled, display_name,
                oidc_issuer, oidc_client_id, oidc_client_secret_encrypted,
                oidc_scopes, oidc_authorize_url, oidc_token_url, oidc_userinfo_url,
                saml_idp_entity_id, saml_idp_sso_url, saml_idp_slo_url, saml_idp_cert,
                saml_sp_entity_id, saml_sp_acs_url, saml_sp_cert,
                saml_sp_private_key_encrypted,
                email_claim, name_claim, sub_claim, updated_at
            )
            VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8,
                $9, $10, $11, $12,
                $13, $14, $15, $16,
                $17, $18, $19,
                $20,
                $21, $22, $23, now()
            )
            ON CONFLICT (organization_id) DO UPDATE SET
                protocol = EXCLUDED.protocol,
                preset = EXCLUDED.preset,
                enabled = EXCLUDED.enabled,
                display_name = EXCLUDED.display_name,
                oidc_issuer = EXCLUDED.oidc_issuer,
                oidc_client_id = EXCLUDED.oidc_client_id,
                oidc_client_secret_encrypted = EXCLUDED.oidc_client_secret_encrypted,
                oidc_scopes = EXCLUDED.oidc_scopes,
                oidc_authorize_url = EXCLUDED.oidc_authorize_url,
                oidc_token_url = EXCLUDED.oidc_token_url,
                oidc_userinfo_url = EXCLUDED.oidc_userinfo_url,
                saml_idp_entity_id = EXCLUDED.saml_idp_entity_id,
                saml_idp_sso_url = EXCLUDED.saml_idp_sso_url,
                saml_idp_slo_url = EXCLUDED.saml_idp_slo_url,
                saml_idp_cert = EXCLUDED.saml_idp_cert,
                saml_sp_entity_id = EXCLUDED.saml_sp_entity_id,
                saml_sp_acs_url = EXCLUDED.saml_sp_acs_url,
                saml_sp_cert = EXCLUDED.saml_sp_cert,
                saml_sp_private_key_encrypted = EXCLUDED.saml_sp_private_key_encrypted,
                email_claim = EXCLUDED.email_claim,
                name_claim = EXCLUDED.name_claim,
                sub_claim = EXCLUDED.sub_claim,
                updated_at = now()
            RETURNING {_IDP_SELECT}
            """,
            organization_id,
            protocol,
            preset,
            enabled,
            display_name,
            oidc_issuer,
            oidc_client_id,
            secret,
            oidc_scopes,
            oidc_authorize_url,
            oidc_token_url,
            oidc_userinfo_url,
            saml_idp_entity_id,
            saml_idp_sso_url,
            saml_idp_slo_url,
            saml_idp_cert,
            saml_sp_entity_id,
            saml_sp_acs_url,
            saml_sp_cert,
            sp_key,
            email_claim,
            name_claim,
            sub_claim,
        )
        if row is None:
            msg = "failed to upsert identity provider"
            raise RuntimeError(msg)
        return _row_to_identity_provider(row)

    async def delete(self, organization_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM organization_identity_providers WHERE organization_id = $1",
            organization_id,
        )


def _row_to_identity_provider(row: asyncpg.Record) -> IdentityProviderRow:
    return IdentityProviderRow(
        organization_id=row["organization_id"],
        protocol=row["protocol"],
        preset=row["preset"],
        enabled=row["enabled"],
        display_name=row["display_name"],
        oidc_issuer=row["oidc_issuer"],
        oidc_client_id=row["oidc_client_id"],
        oidc_client_secret_encrypted=row["oidc_client_secret_encrypted"],
        oidc_scopes=row["oidc_scopes"],
        oidc_authorize_url=row["oidc_authorize_url"],
        oidc_token_url=row["oidc_token_url"],
        oidc_userinfo_url=row["oidc_userinfo_url"],
        saml_idp_entity_id=row["saml_idp_entity_id"],
        saml_idp_sso_url=row["saml_idp_sso_url"],
        saml_idp_slo_url=row["saml_idp_slo_url"],
        saml_idp_cert=row["saml_idp_cert"],
        saml_sp_entity_id=row["saml_sp_entity_id"],
        saml_sp_acs_url=row["saml_sp_acs_url"],
        saml_sp_cert=row["saml_sp_cert"],
        saml_sp_private_key_encrypted=row["saml_sp_private_key_encrypted"],
        email_claim=row["email_claim"],
        name_claim=row["name_claim"],
        sub_claim=row["sub_claim"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
