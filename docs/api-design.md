# API Design

## Style

The HTTP API follows a pragmatic REST-style design implemented with FastAPI.

Current characteristics:

- versioned routes under `/api/v1`
- JSON request and response bodies
- Pydantic schemas for validation and serialization
- cookie-based session authentication for browser clients
- explicit permission checks in route handlers

The API is the backend contract consumed by the React frontend and by inbound webhook providers.

## Route organization

Top-level router registration lives in `backend/app/api/router.py`.

Major route groups:

- `install`: first-run bootstrap
- `auth`: login, session, identity provider discovery, current user
- `reviews`: review list, detail, retry
- `teams`: team management and team members
- `teams/{team_id}/repos`: repository integrations scoped to a team
- `repositories`: organization-wide repository listing
- `settings/identity-provider`: SSO configuration
- `settings/llm-providers`: LLM provider management
- `settings/rbac`: RBAC catalog and permission matrix
- `users`: organization user management
- `webhooks`: Git provider inbound webhooks
- `agent`: callback endpoint for agent review events

## Versioning

The current public API version is `v1`.

Versioning is path-based:

- `/api/v1/...`

This keeps the frontend contract stable while allowing future incompatible changes to be introduced under a new version prefix.

## Authentication model

The browser-facing API uses a session cookie:

- cookie name: `cogito_session`
- session storage: Redis
- current user endpoint: `GET /api/v1/auth/me`

Authentication modes:

- local username/password for first-run and administrator fallback
- OIDC SSO
- SAML 2.0 SSO
- dev bypass when auth is disabled and setup is complete

Webhook and agent callback endpoints use signature-based verification instead of browser sessions.

## Authorization model

Authorization is action-based and enforced in the backend.

Typical route guards use:

- `require_org_action_dep(...)`
- `require_team_action_dep(...)`
- `assert_review_access(...)`

RBAC details are documented separately in `docs/rbac.md`.

## Response conventions

Common conventions visible in the current API:

- list endpoints return `{ items, total }`
- missing resources return `404`
- permission failures return `403`
- invalid signatures return `401`
- ignored webhook events commonly return `202`
- setup or auth flow issues return explicit `400` or `403` errors

## Pagination

Paginated endpoints use a shared pagination helper and return:

- `items`
- `total`

The frontend drives page state with query parameters and translates page numbers into limit and offset values.

## Webhook design

Webhook endpoints are provider-specific and integration-specific.

Current pattern:

- `/api/v1/webhooks/github/{integration_id}`
- `/api/v1/webhooks/gitlab/{integration_id}`
- `/api/v1/webhooks/azure-devops/{integration_id}`
- `/api/v1/webhooks/bitbucket/{integration_id}`
- `/api/v1/webhooks/bitbucket-dc/{integration_id}`

Each handler:

1. loads the repository integration
2. verifies the configured provider type
3. validates the webhook signature
4. parses the provider-specific payload
5. deduplicates by delivery id or repo/PR/SHA
6. creates a pending review row
7. enqueues a Celery review job

Legacy global webhook endpoints still exist for some providers but now return `410 Gone`.

## Agent callback design

The agent does not update the database directly.

Instead it reports events to:

- `POST /api/v1/agent/review-events`

The backend validates:

- HMAC signature
- callback payload schema
- review existence

Then it applies state transitions and stores findings.

## OpenAPI

The backend exposes a standard FastAPI OpenAPI document.

The project uses this contract to generate frontend TypeScript types:

- export command: `make openapi`
- generated file: `frontend/src/api/generated/schema.ts`

## Design principles visible in code

- route handlers stay thin
- business logic sits in services
- SQL access sits in repositories
- schemas define the contract at API boundaries
- provider-specific logic is isolated behind abstractions

This keeps the API layer readable and easier to evolve.
