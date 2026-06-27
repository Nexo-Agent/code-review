-- migrate:up

CREATE TABLE IF NOT EXISTS organization_identity_providers (
  organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  protocol TEXT NOT NULL CHECK (protocol IN ('oidc', 'saml')),
  preset TEXT NOT NULL CHECK (preset IN (
    'google', 'okta', 'keycloak', 'entra', 'auth0', 'custom'
  )),
  enabled BOOLEAN NOT NULL DEFAULT false,
  display_name TEXT NOT NULL DEFAULT '',
  oidc_issuer TEXT,
  oidc_client_id TEXT,
  oidc_client_secret_encrypted TEXT,
  oidc_scopes TEXT NOT NULL DEFAULT 'openid email profile',
  oidc_authorize_url TEXT,
  oidc_token_url TEXT,
  oidc_userinfo_url TEXT,
  saml_idp_entity_id TEXT,
  saml_idp_sso_url TEXT,
  saml_idp_slo_url TEXT,
  saml_idp_cert TEXT,
  saml_sp_entity_id TEXT,
  saml_sp_acs_url TEXT,
  saml_sp_cert TEXT,
  saml_sp_private_key_encrypted TEXT,
  email_claim TEXT NOT NULL DEFAULT 'email',
  name_claim TEXT NOT NULL DEFAULT 'name',
  sub_claim TEXT NOT NULL DEFAULT 'sub',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- migrate:down

DROP TABLE IF EXISTS organization_identity_providers;
