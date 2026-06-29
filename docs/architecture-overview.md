# Architecture Overview

## System purpose

Cogito Review is an AI-assisted code review platform that listens to pull request or merge request events, runs an isolated coding-agent review, stores the results, and exposes them in a web application.

The system is built around one core workflow:

1. a Git provider sends a webhook for a PR or MR change
2. the backend validates and records a review request
3. the worker launches an isolated review agent
4. the agent analyzes the code and posts comments back to the Git provider
5. the agent reports findings to the backend
6. the frontend displays runs, findings, and operational settings

## Main components

### Backend

The backend is a FastAPI application responsible for:

- serving the REST API
- serving the built frontend SPA
- handling install and authentication flows
- storing and querying application state in PostgreSQL
- validating inbound webhooks
- receiving callback events from the review agent
- enforcing RBAC permissions

### Frontend

The frontend is a React single-page application responsible for:

- install and login flows
- team and repository management
- LLM provider configuration
- SSO and RBAC settings
- review list and review detail screens

### Worker

The worker is a Celery process that:

- consumes queued review jobs from Redis
- resolves review runtime configuration from PostgreSQL
- starts the isolated review agent through the runtime provider

### Agent executor

The agent executor is a separate one-shot container that:

- prepares the repository workspace
- runs OpenCode with the bundled review skill
- posts inline and summary comments to the Git provider
- sends lifecycle callbacks and findings to the backend

## Shared packages

The repository is a workspace monorepo with three Python packages:

- `shared/`: provider protocols, git and CI providers, workspace tooling, runtime specs, callback schema
- `backend/`: API, services, persistence, auth, RBAC, worker entrypoints
- `agent/`: review runner, MCP server, OpenCode integration

This allows backend and agent to share protocols and provider logic without duplicating implementation.

## Current high-level flow

```text
Git webhook
  -> FastAPI webhook endpoint
  -> Review row in PostgreSQL
  -> Celery task in Redis
  -> Worker resolves repo + LLM config
  -> Runtime spawns one-shot agent container
  -> Agent prepares git worktree and CI summary
  -> OpenCode review run
  -> Inline comments + summary comment posted to provider
  -> Callback event to backend
  -> Findings persisted in PostgreSQL
  -> Frontend reads review state and findings
```

## Integration boundaries

### Git providers

Current Git provider support:

- GitHub
- GitLab
- Azure DevOps
- Bitbucket Cloud
- Bitbucket Data Center

Each provider is responsible for:

- webhook validation
- webhook payload parsing
- PR or MR metadata retrieval
- repository clone access
- PR or MR comment publishing
- blob URL generation for findings

### CI providers

CI context is optional and provider-specific.

Current CI support:

- GitHub Actions
- GitLab CI
- Bitbucket Cloud pipelines
- Bitbucket Data Center builds
- no-op fallback for providers without CI integration in this codebase

### Identity providers

Current authentication integration support:

- OIDC
- SAML 2.0
- local bootstrap login

### LLM providers

LLM configuration is stored in PostgreSQL and materialized into OpenCode-compatible provider configuration at runtime.

The current model is “OpenAI-compatible endpoint profiles” rather than hard-coded vendor SDK integrations.

## Data ownership

### PostgreSQL

Primary persistent state:

- reviews and review findings
- teams and memberships
- users and organization roles
- repository integrations
- LLM providers
- identity provider configuration
- RBAC catalog and permission matrix
- audit events

### Redis

Ephemeral operational state:

- Celery broker and backend
- browser session records
- auth/session support data

### Workspace volume

Ephemeral or semi-persistent git workspace state:

- repository mirrors
- per-review worktrees

## Architectural characteristics

- API and frontend are deployed together in one main application image
- worker runs separately but shares the same Python application codebase
- agent execution is isolated in a dedicated image
- backend is the source of truth for application state
- agent communicates by callback, not direct database access
- permissions are enforced server-side
- runtime abstraction exists, but Docker is the only implemented review runtime today

## Current maturity notes

Implemented and in active use:

- multi-team repository management
- multi-provider Git integration
- review persistence and retry
- OpenCode-based review execution
- OIDC and SAML configuration
- RBAC permission enforcement

Present in architecture but not fully implemented:

- Kubernetes review runtime execution
- broader work-management integrations such as Jira or Trello
- analytics-oriented system modules beyond current review and audit data
