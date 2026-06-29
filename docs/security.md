# Security

## Security boundaries

The system has four major security boundaries:

- browser user authentication and authorization
- Git provider webhook authenticity
- agent callback authenticity
- storage and handling of operational secrets

## Authentication

### Browser login modes

Current supported modes:

- local administrator login
- OIDC SSO
- SAML 2.0 SSO

When authentication is disabled for local development, the backend may create a dev admin identity after setup completes.

### Session model

- session cookie name: `cogito_session`
- session data stored in Redis
- session TTL controlled by `COGITO_REVIEW_SESSION_TTL_SECONDS`
- cookie is `HttpOnly`
- cookie `Secure` depends on auth mode and frontend URL

## Authorization

Authorization is enforced in the backend through RBAC.

Security-relevant principles:

- UI visibility does not grant access
- API handlers check permissions server-side
- review access is team-scoped
- settings changes require explicit org-scoped permissions

RBAC details are documented in `docs/rbac.md`.

## Webhook verification

Inbound Git webhooks are validated per provider using the configured repository integration secrets.

Current verification mechanisms include:

- GitHub HMAC SHA-256
- GitLab token or signed webhook verification
- Azure DevOps Basic-auth-style shared credential pair
- Bitbucket Cloud HMAC
- Bitbucket Data Center Basic-auth-style shared credential pair

Webhook processing does not proceed unless signature verification succeeds.

## Agent callback verification

The review agent reports back to the backend through:

- `POST /api/v1/agent/review-events`

Security controls:

- HMAC SHA-256 signature in `X-Review-Signature-256`
- callback payload schema validation
- review existence check before state mutation

This prevents arbitrary unauthenticated callback writes into review state.

## Secret handling

Sensitive operational values include:

- LLM API tokens
- Git provider tokens
- webhook secrets
- OIDC client secrets
- SAML private keys

Current storage pattern:

- persisted in PostgreSQL where applicable
- selected secrets encrypted using Fernet
- only “configured” booleans returned to the browser for sensitive fields

The encryption key is derived from:

- `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY`, or
- `COGITO_REVIEW_SESSION_SECRET` as fallback

Production deployments should provide a dedicated encryption key instead of relying on the fallback.

## Agent isolation

The agent is intentionally isolated from the main application database.

Security properties of this boundary:

- agent receives only per-review runtime inputs
- agent cannot directly mutate backend data stores
- agent exits after one review run
- review state returns through an authenticated callback channel

## Workspace and runtime risk

The current review runtime uses Docker and requires worker access to the Docker socket.

This is operationally powerful and should be treated as privileged host access.

Deployment implications:

- keep worker access restricted
- do not expose the Docker socket more broadly than necessary
- keep the agent image minimal

## SSO configuration safety

The identity provider service includes some defensive behavior:

- OIDC uses issuer discovery or explicit endpoint override
- SAML metadata URL validation requires HTTPS
- SAML metadata URL resolution rejects private, loopback, and reserved addresses

This reduces the chance of unsafe remote metadata fetches.

## Setup and bootstrap security

The initial local superuser can only be created while the system is in setup-required state.

After bootstrap:

- setup is marked complete
- repeated bootstrap attempts are rejected

This prevents accidental recreation of the initial admin through the install endpoint.

## Current security posture summary

Implemented:

- backend-side RBAC checks
- signed webhook validation
- signed agent callbacks
- session-backed login
- encrypted storage for selected secrets
- isolated callback-only agent execution

Important operational caveats:

- Docker socket access on the worker is highly privileged
- PostgreSQL still stores operational credentials and must be protected accordingly
- Kubernetes isolation path is not yet implemented
