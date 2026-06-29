# Database

## Overview

The primary system database is PostgreSQL.

PostgreSQL stores:

- users and organizations
- teams and memberships
- repository integrations
- LLM providers
- identity provider configuration
- reviews and findings
- RBAC catalog and permission matrix
- audit events

Redis is also used by the system, but only for sessions and background job state. It is not part of the relational domain model.

## Migration model

Schema changes are managed with `dbmate`.

- migration directory: `backend/migrations/`
- style: SQL files with `-- migrate:up` and `-- migrate:down`

The migration history shows the evolution from a simple review application to a multi-team, RBAC-enabled system with SSO support.

## Core domain tables

### Reviews

Main table: `reviews`

Important columns:

- provider
- repo_full_name
- pr_number
- head_sha
- status
- team_id
- repo_integration_id
- PR metadata such as title, author, refs, and URL
- delivery stats for summary and inline comments
- timestamps for created, started, and completed states

Uniqueness and deduplication:

- unique `(repo_full_name, pr_number, head_sha)`
- unique `delivery_id` when available

### Review findings

Main table: `review_findings`

Each finding belongs to one review and stores:

- severity
- file_path
- line_start
- line_end
- title
- body

Findings are replaced on review completion rather than incrementally appended.

## Organization and team model

### Organizations

Table: `organizations`

Current behavior is effectively single-organization per deployment. A default organization row is seeded by migration.

### Teams

Table: `teams`

Each team belongs to an organization and owns repository integrations and review visibility.

### Team members

Table: `team_members`

Each row links:

- `team_id`
- `user_id`
- `role_id`

The legacy string role column was replaced by RBAC-backed `role_id`.

## User model

Table: `users`

Important columns visible in code:

- `oidc_sub`
- `email`
- `name`
- `is_org_admin`
- `auth_source`
- `username`
- `password_hash`
- `is_superuser`

The table supports both SSO identities and local administrator accounts.

## Repository integrations

Table: `repo_integrations`

Each integration belongs to a team and stores provider-specific configuration.

Common columns:

- name
- team_id
- git_provider
- repo_full_name
- llm_provider_id override
- enabled
- system_prompt

Provider-specific credential groups:

- GitHub token and webhook secret
- Azure DevOps organization, project, PAT, and webhook basic-auth pair
- GitLab base URL, token, and webhook secret
- Bitbucket Cloud token and webhook secret
- Bitbucket Data Center base URL, token, and webhook basic-auth pair

`repo_full_name` may be empty to act as a catch-all integration for a team.

## LLM providers

Table: `llm_providers`

Important fields:

- name
- provider_id
- base_url
- api_token
- model
- opencode_model
- is_default
- enabled
- organization_id

The current design stores reusable endpoint profiles per organization, with optional repository-level overrides through `repo_integrations.llm_provider_id`.

## Identity provider configuration

Table: `organization_identity_providers`

One row per organization stores either:

- OIDC settings
- or SAML settings

Sensitive fields such as client secrets and SAML private keys are stored encrypted.

## RBAC tables

RBAC is documented in detail in `docs/rbac.md`.

Main tables:

- `rbac_roles`
- `rbac_actions`
- `rbac_resource_scopes`
- `rbac_role_permissions`
- `organization_user_roles`

## Audit tables

Table: `audit_events`

Currently used for:

- permission matrix updates
- organization role changes

Audit coverage exists but is not yet comprehensive across every mutable workflow.

## Legacy and removed concepts

The migration history shows an older `projects` concept introduced and later removed.

Current domain model is:

- organization
- team
- repository integration
- review

There is no active `projects` layer in the current schema.

## Secret storage

Some operational secrets are stored in PostgreSQL:

- LLM API tokens
- repository integration credentials
- OIDC client secrets
- SAML private keys

Application code encrypts selected secret values before storage using a Fernet key derived from:

- `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY`, or
- `COGITO_REVIEW_SESSION_SECRET` as fallback

Not every credential path is abstracted the same way in the schema, but the system treats the database as the persistent store for operational configuration.

## Current schema characteristics

- relational source of truth is PostgreSQL
- default organization is seeded
- review partitioning is team-based
- repository integrations are team-scoped
- current schema is designed for one deployed organization with multiple teams
