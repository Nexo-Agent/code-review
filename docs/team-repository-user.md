# Team, Repository, And User Model

## Overview

The current system organizes access and review ownership around teams.

High-level model:

- one deployed organization
- many teams
- many users
- many repository integrations owned by teams
- reviews scoped to the team that owns the repository integration

## Organization model

The database contains an `organizations` table, but the current product behavior is effectively single-organization per deployment.

A default organization is seeded by migration and used throughout the backend services.

## Users

Users are stored in the `users` table.

Important current attributes:

- identity subject (`oidc_sub`)
- email
- display name
- auth source
- optional local username
- local superuser flag
- organization admin flag

User sources:

- local bootstrap and local admin login
- SSO through OIDC
- SSO through SAML

## Organization roles

A user can hold organization-level RBAC roles through `organization_user_roles`.

Current organization roles:

- `org_admin`
- `org_member`

These roles govern organization-wide capabilities such as settings and user administration.

## Teams

Teams are the main collaboration and access partition in the current system.

Each team has:

- id
- organization_id
- name
- slug

Teams are visible through:

- teams list pages
- team detail pages
- team member APIs
- team repository APIs

## Team memberships

Team membership is stored in `team_members`.

A membership links one user to one team with an RBAC-backed team role.

Current team role keys:

- `team_admin`
- `member`
- `viewer`

These roles affect what a user can do inside that team, including repository and review operations.

## Repository integrations

Repositories are not modeled as a global standalone source-control catalog.

Instead, the current product stores “repository integrations” that combine:

- repository identity
- Git provider selection
- provider credentials and webhook secrets
- optional repository-specific LLM override
- enabled flag
- optional custom review system prompt

Every repository integration belongs to exactly one team.

## Repository matching model

`repo_integrations.repo_full_name` may be:

- a concrete repository identifier such as `owner/repo`
- or empty, meaning a catch-all integration for the team

Resolution order prefers exact match, then catch-all.

## Reviews

Every review row stores `team_id`.

This means:

- review visibility is team-scoped
- review retry permission is team-scoped
- repository ownership and review ownership are aligned

## Relationship summary

Current relationship shape:

- organization has many teams
- organization has many users
- users may have organization roles
- users may belong to many teams
- teams have many repository integrations
- teams have many reviews
- reviews have many findings

## Frontend presentation

### Teams page

Shows:

- team name
- member count
- repository count

### Team detail

Shows:

- team members
- repositories owned by the team
- team settings actions based on permission

### Repositories page

Shows organization-wide repository integrations, but each row still belongs to one team.

### Users page

Shows:

- identity information
- organization admin status
- team memberships summary

## Current product boundaries

Implemented:

- multi-team ownership and access
- user provisioning and membership assignment
- team-scoped repository integrations
- team-scoped review access

Not present in the current model:

- multiple organizations per deployed app as a first-class product experience
- nested repository groups under teams beyond the integration list
- separate project layer between team and repository
