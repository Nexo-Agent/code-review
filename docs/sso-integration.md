# SSO Integration

## Purpose

SSO integration allows browser users to authenticate through an organization identity provider instead of relying only on local administrator accounts.

Current supported protocols:

- OIDC
- SAML 2.0

Configuration is organization-scoped and stored in PostgreSQL.

## Data model

SSO settings are stored in:

- `organization_identity_providers`

The current model supports one configured identity provider per organization.

Key configuration groups:

- protocol and preset
- enabled flag
- display name
- OIDC issuer, client id, client secret, scopes, optional manual endpoints
- SAML IdP entity id, SSO URL, SLO URL, certificate
- SAML SP entity id, ACS URL, SP certificate, SP private key
- claim mapping for email, name, and subject

## Public API surface

### Browser-facing discovery

- `GET /api/v1/auth/idp`

Used by the login screen to know whether SSO is enabled and which provider name to display.

### Admin settings

- `GET /api/v1/settings/identity-provider`
- `PUT /api/v1/settings/identity-provider`
- `DELETE /api/v1/settings/identity-provider`
- `PUT /api/v1/settings/identity-provider/saml/cert`

### Login flow

- `GET /api/v1/auth/login`
- `GET /api/v1/auth/callback` for OIDC
- `GET /api/v1/auth/saml/login`
- `POST /api/v1/auth/saml/acs`
- `GET /api/v1/auth/saml/metadata`

## OIDC design

OIDC behavior lives primarily in:

- `backend/app/auth/oidc.py`
- `backend/app/services/identity_provider.py`

Current flow:

1. admin configures issuer and client credentials
2. backend builds authorization URL
3. user is redirected to the provider
4. backend exchanges authorization code for tokens
5. backend fetches userinfo
6. mapped claims are normalized into local user fields
7. local session is created

The backend supports:

- standard OIDC discovery from issuer
- optional manual override of authorization, token, and userinfo endpoints

## SAML design

SAML behavior lives primarily in:

- `backend/app/auth/saml.py`
- `backend/app/services/identity_provider.py`

Current flow:

1. admin configures the IdP or imports metadata
2. backend ensures SP credentials exist
3. user is redirected to the IdP login
4. assertion is posted to the ACS endpoint
5. backend validates the response and extracts attributes
6. mapped claims are normalized into local user fields
7. local session is created

## SP certificate handling

For SAML, the system can:

- generate an SP certificate and private key automatically when needed
- accept manual SP cert and private key upload through the settings API

Generated values are stored in the identity provider row, with the private key encrypted.

## Provider presets

The UI and backend support preset-driven configuration for common providers.

Examples visible in the code:

- Google
- Entra
- Okta
- Keycloak
- Auth0
- Custom
- SAML

Presets mainly influence display defaults and expected configuration shape.

## Claim mapping

The current model supports configurable claims for:

- email
- name
- subject

This is important because OIDC and SAML providers often use different claim names.

## User provisioning

On successful SSO login, the backend provisions or updates the user in the local database.

Current behavior:

- user identity is stored as an external subject
- auth source is `sso`
- organization role defaults are synchronized if missing
- later logins update email and name

The system does not depend on SCIM or external directory sync for basic account creation.

## Security considerations

- OIDC client secrets are stored encrypted
- SAML SP private keys are stored encrypted
- SAML metadata fetch requires HTTPS and rejects private-address targets
- redirect targets are normalized against the configured frontend origin

## Frontend behavior

The login page:

- checks whether SSO is enabled
- shows a provider-branded “Continue with ...” button when configured
- still allows local administrator sign-in as fallback

The settings page supports:

- choosing a provider preset
- creating or editing configuration
- removing the configured identity provider

## Current limitations

- one identity provider configuration per organization
- no multi-provider login chooser for end users
- no SCIM provisioning layer
- no advanced group-to-role synchronization built into the current SSO flow
