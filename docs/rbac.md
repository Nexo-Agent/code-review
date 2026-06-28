# RBAC Reference

## Status

**Implemented** — this document describes the RBAC system as shipped in Cogito Review.

## Overview

Cogito Review uses a hybrid Role-Based Access Control (RBAC) model:

| Layer | Mutable at runtime? | Storage |
|-------|---------------------|---------|
| Roles, actions, resource scopes (catalog) | No — migrations only | `rbac_*` catalog tables |
| Allowed action matrix (policy) | Yes — org admin UI | `rbac_role_permissions` |
| Role assignments | Yes — via existing user/team APIs | `organization_user_roles`, `team_members.role_id` |

Authorization is **action-based**, not page-based. The backend is the source of truth; the frontend reads effective permissions from `GET /api/v1/auth/me` and hides or disables UI accordingly. Denied API calls still return `403`.

### Conceptual flow

```
Principal → Assigned Role → Allowed Action @ Resource Scope → Allow / Deny
```

- **Principal**: authenticated user (session cookie)
- **Assigned role**: organization role (`org_admin`, `org_member`) and/or team role (`team_admin`, `member`, `viewer`)
- **Action**: namespaced operation (e.g. `review.rerun`)
- **Resource scope**: evaluation boundary (`team`, `settings`, `organization`, …)

Review data is partitioned by **team**. Repository and review actions are enforced at **team scope** even though catalog scopes like `repository` and `review` exist for semantics and future use.

---

## Design principles

1. **Review-first** — permissions map to workflows (`review.rerun`, `repo.update`), not UI routes (`can_open_settings_page`).
2. **Action-based enforcement** — route handlers call `PermissionChecker.require(action, team_id=…)`; business logic must not branch on role names.
3. **Immutable catalog** — new roles/actions/scopes require a forward migration and code update in `backend/app/rbac/catalog.py`.
4. **Mutable policy matrix** — org admins can toggle which team roles may perform which team-scoped actions (see [Permission matrix UI](#permission-matrix-ui)).
5. **Deny by default** — missing matrix entry or missing role assignment yields denial.

---

## Roles

Seeded in migration [`backend/migrations/015_rbac_foundation.sql`](../backend/migrations/015_rbac_foundation.sql).

| Role key | Scope kind | Assignment | Purpose |
|----------|------------|------------|---------|
| `org_admin` | organization | `organization_user_roles` | Full org administration |
| `org_member` | organization | `organization_user_roles` | Default org role; minimal org-level permissions |
| `team_admin` | team | `team_members.role_id` | Team administration and operations |
| `member` | team | `team_members.role_id` | Operational contributor |
| `viewer` | team | `team_members.role_id` | Read-only within a team |

### Superuser (break-glass)

Local install accounts may have `users.is_superuser = true`. This is **not** a business RBAC role.

- Used for first-boot install and local login only.
- On creation, the user is assigned `org_admin` in `organization_user_roles` and `is_org_admin` is set.
- **Does not bypass** `PermissionChecker`; authorization goes through the same matrix as other users with `org_admin`.

---

## Actions and default scopes

Defined in [`backend/app/rbac/catalog.py`](../backend/app/rbac/catalog.py) as `ActionKey`. Each action has a default scope via `ACTION_DEFAULT_SCOPE`.

### Organization / settings / user actions

Evaluated against organization roles only (no `team_id` required):

| Action | Default scope |
|--------|---------------|
| `team.create` | `organization` |
| `team.delete` | `organization` |
| `user.read` | `user` |
| `user.assign_org_admin` | `user` |
| `user.deactivate` | `user` |
| `settings.sso.read` | `settings` |
| `settings.sso.update` | `settings` |
| `settings.llm.read` | `settings` |
| `settings.llm.update` | `settings` |
| `settings.rbac.read` | `settings` |
| `settings.rbac.update` | `settings` |

### Team-scoped actions

Evaluated against organization role (for `org_admin` override) and/or team role for the target `team_id`:

| Action | Default scope |
|--------|---------------|
| `team.read` | `team` |
| `team.update` | `team` |
| `team.member.read` | `team` |
| `team.member.add` | `team` |
| `team.member.update_role` | `team` |
| `team.member.remove` | `team` |
| `repo.read` | `team` |
| `repo.create` | `team` |
| `repo.update` | `team` |
| `repo.delete` | `team` |
| `repo.configure_credentials` | `team` |
| `review.read` | `team` |
| `review.rerun` | `team` |
| `review.finding.read` | `team` |

### Catalog-only actions (not yet on dedicated routes)

These actions are seeded and included in the default policy matrix but are **not** checked on separate API endpoints yet:

- `user.deactivate` — no deactivate-user route
- `team.member.update_role` — role changes go through member add/upsert; no dedicated update endpoint
- `repo.configure_credentials` — credential updates use `repo.update` on the same PUT handler

When adding new features, prefer wiring enforcement to the most specific action key.

---

## Default policy matrix

Seeded in `015_rbac_foundation.sql`. Org admins may change **team-scoped** rows via the UI; org-admin rows are fixed (full allow).

| Role | Team scope (summary) |
|------|----------------------|
| `org_admin` | All actions on all scopes (including org/settings/user) |
| `team_admin` | Full team admin + repo + review operations |
| `member` | Read team/repo/review; **includes `review.rerun`** (configurable via matrix) |
| `viewer` | Read-only; **no** `review.rerun`, no repo/team mutations |
| `org_member` | `team.read` @ organization scope; `settings.llm.read` @ settings scope |

### Product decisions (locked in implementation)

| Question | Decision |
|----------|----------|
| Can `member` rerun reviews? | **Yes by default**; org admins can revoke via permission matrix |
| Superuser bypass RBAC? | **No** — superuser receives `org_admin` assignment |
| Separate credential action? | Action exists (`repo.configure_credentials`); routes currently use `repo.update` |
| Policy ownership | Single-organization install; matrix is global per deployment |

---

## Database schema

### Catalog (immutable at runtime)

- `rbac_roles` — role definitions (`key`, `display_name`, `scope_kind`, …)
- `rbac_actions` — action definitions
- `rbac_resource_scopes` — scope definitions

### Policy (mutable)

- `rbac_role_permissions` — `(role_id, action_id, resource_scope_id, allowed)` with unique constraint

### Assignments

- `organization_user_roles` — `(organization_id, user_id, role_id)`
- `team_members.role_id` — FK to `rbac_roles` (replaces legacy string `role` column)

### Audit

- `audit_events` — migration [`016_audit_events.sql`](../backend/migrations/016_audit_events.sql)

Logged today:

| Event type | Trigger |
|------------|---------|
| `permission_matrix.updated` | `PUT /api/v1/settings/rbac/permissions` |
| `organization_role.changed` | `PUT /api/v1/users/{id}/organization-role` |

Team membership changes are not yet written to `audit_events`.

### Legacy compatibility

`users.is_org_admin` is **kept in sync** when organization roles change (`RbacRepository.set_organization_role`). It is used as a fallback when `organization_user_roles` has no rows (e.g. pre-migration dev data). New authorization logic should use `PermissionChecker`, not `is_org_admin` directly.

---

## Permission resolution

Implementation: [`backend/app/rbac/checker.py`](../backend/app/rbac/checker.py)

### Step 1 — Resolve organization roles

Load from `organization_user_roles`. Fallback:

- `is_org_admin` or `is_superuser` → treat as `org_admin`
- otherwise → `org_member`

### Step 2 — Classify action

- **Org/settings/user actions** (`ORG_SCOPED_ACTIONS` or scope ∈ `{organization, user, settings}`): check org role against matrix at the action's default scope.
- **Team actions**: require `team_id`; see step 3.

### Step 3 — Team action evaluation

1. If user has `org_admin` org role **and** matrix allows the action at team scope → **allow**.
2. Else load team role from `team_members` for `(user_id, team_id)` and check matrix → **allow** or **deny**.
3. No matching allow → **deny**.

### Effective permissions

[`backend/app/rbac/effective_permissions.py`](../backend/app/rbac/effective_permissions.py) computes what the frontend needs:

- `organization_actions` — allowed org/settings/user actions
- `team_actions` — map of `team_id → [action keys]`
- `organization_roles`, `team_memberships`

`org_admin` users receive all teams in `team_ids` / `team_actions` even without team membership rows.

### Caching

[`PermissionCache`](../backend/app/rbac/repositories.py) holds the role-permission matrix in memory per process. Cache is invalidated on `PUT /api/v1/settings/rbac/permissions`.

---

## Backend module layout

```
backend/app/rbac/
├── catalog.py              # ActionKey, RoleKey, ScopeKey, ACTION_DEFAULT_SCOPE
├── models.py               # PermissionDecision, EffectivePermissions, …
├── repositories.py         # DB access, matrix CRUD, PermissionCache
├── checker.py              # PermissionChecker.can / require
├── effective_permissions.py
└── dependencies.py         # require_action_on_review, require_action_on_repo, …

backend/app/auth/dependencies.py   # require_permission, require_org_action_dep, require_team_action_dep
backend/app/services/access_control.py   # get_accessible_team_ids (RBAC-backed)
backend/app/services/audit.py          # log_audit_event
```

---

## API enforcement map

Protected routes use `require_org_action_dep(ActionKey.…)` or `require_team_action_dep(ActionKey.…)` from [`backend/app/auth/dependencies.py`](../backend/app/auth/dependencies.py).

| Area | Route | Action |
|------|-------|--------|
| Teams | `POST /teams` | `team.create` |
| Teams | `PUT /teams/{id}` | `team.update` |
| Teams | `DELETE /teams/{id}` | `team.delete` |
| Teams | `GET …/members` | `team.member.read` |
| Teams | `POST …/members` | `team.member.add` |
| Teams | `DELETE …/members/{user_id}` | `team.member.remove` |
| Team repos | `GET/POST/PUT/DELETE …/repos/*` | `repo.read/create/update/delete` |
| Reviews | `GET /reviews/{id}` | `review.read` |
| Reviews | `POST /reviews/{id}/retry` | `review.rerun` |
| Users | `GET /users`, `GET /auth/users` | `user.read` |
| Users | `PUT /users/{id}/organization-role` | `user.assign_org_admin` |
| LLM providers | `POST/PUT/DELETE …/llm-providers` | `settings.llm.update` |
| Identity provider | `GET …/identity-provider` | `settings.sso.read` |
| Identity provider | `PUT/DELETE …/identity-provider` | `settings.sso.update` |
| RBAC settings | `GET …/rbac/catalog`, `GET …/rbac/permissions` | `settings.rbac.read` |
| RBAC settings | `PUT …/rbac/permissions` | `settings.rbac.update` |

List endpoints (`GET /reviews`, `GET /teams`, …) filter by **accessible team IDs** derived from effective permissions, not merely membership.

Exempt from session RBAC: webhooks, agent callbacks, health, install bootstrap, auth login/callback.

### Example: retry review

```python
review = await ReviewRepository(conn).get(review_id)
await assert_review_access(
    conn, user, review.team_id, action=ActionKey.REVIEW_RERUN
)
```

---

## Auth API

### `GET /api/v1/auth/me`

Returns session user plus RBAC context ([`MeResponse`](../backend/app/schemas/auth.py)):

```json
{
  "user": { "id": "…", "email": "…", "is_org_admin": true, … },
  "team_ids": ["…"],
  "auth_enabled": true,
  "organization_roles": ["org_admin"],
  "team_memberships": [
    { "team_id": "…", "role_key": "team_admin" }
  ],
  "permissions": {
    "organization": ["settings.sso.read", "user.read", …],
    "teams": {
      "<team-uuid>": ["team.read", "repo.read", "review.rerun", …]
    }
  }
}
```

There is no separate `GET /auth/permissions` endpoint; permissions are included on `/me`.

### RBAC admin API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/settings/rbac/catalog` | Roles, actions, scopes (read-only) |
| `GET` | `/api/v1/settings/rbac/permissions` | Full permission matrix |
| `PUT` | `/api/v1/settings/rbac/permissions` | Batch update `{ updates: [{ role_key, action_key, scope_key, allowed }] }` |

### Organization role assignment

`PUT /api/v1/users/{user_id}/organization-role`

```json
{ "role_key": "org_admin" }
```

Allowed values: `org_admin`, `org_member`. Requires `user.assign_org_admin`. Syncs `is_org_admin` and writes an audit event.

---

## Frontend

### Permission helpers

- [`frontend/src/lib/permissions.ts`](../frontend/src/lib/permissions.ts) — `hasOrgPermission`, `hasTeamPermission`, `isOrgAdmin`, route guards
- [`frontend/src/hooks/use-permission.ts`](../frontend/src/hooks/use-permission.ts) — `usePermission(action, teamId?)`, `useOrgPermission(action)`

Fallback: if `permissions` is null (older API), org UI checks `user.is_org_admin`.

### Navigation and route guards

Sidebar ([`AppShell.tsx`](../frontend/src/components/layout/AppShell.tsx)) shows Organization items based on effective permissions:

| Nav item | Required action |
|----------|-----------------|
| Users | `user.read` |
| LLM Provider | `settings.llm.read` |
| SSO | `settings.sso.read` |
| Permissions | `settings.rbac.read` |

Route `beforeLoad` guards use `requireOrgPermission(…)` on admin pages.

### Permission matrix UI

**Path:** `/settings/permissions`
**Sidebar:** Organization → Permissions

MVP scope:

- Rows: team-scoped actions
- Columns: team roles (`team_admin`, `member`, `viewer`)
- Toggle updates a single matrix cell via `PUT /api/v1/settings/rbac/permissions`
- `org_admin` column is shown but checkboxes are disabled (org permissions are not editable in UI)

Other UI driven by permissions:

- Create team → `team.create`
- Team settings / add repo / add member → `team.update`, `repo.create`, `team.member.add`
- Re-review button → `review.rerun` for the review's team

Team member roles are assigned on **Teams → Members** (values: `team_admin`, `member`, `viewer`).

---

## Provisioning and role assignment

| Event | Org role | Team role |
|-------|----------|-----------|
| Install bootstrap (local superuser) | `org_admin` | — |
| SSO JIT user (first org admin / bootstrap email) | `org_admin` or `org_member` | — |
| `UserRepository.upsert_external_user` (new user) | `org_member` if no row exists | — |
| `TeamMemberRepository.add` | — | `member` / `viewer` / `team_admin` (API string key → `role_id`) |
| `PUT …/organization-role` | `org_admin` / `org_member` | — |

Migration backfill (`015_rbac_foundation.sql`):

- `is_org_admin = true` or `is_superuser = true` → `org_admin`
- All other users → `org_member`
- Legacy `team_members.role` text → corresponding `role_id`

---

## Adding a new permission

1. Add action (and scope if needed) in a **new dbmate migration** — insert into `rbac_actions` / `rbac_resource_scopes`, seed default `rbac_role_permissions` rows.
2. Add constant to `ActionKey` / `ACTION_DEFAULT_SCOPE` in `catalog.py`.
3. Enforce in the relevant API route via `require_permission` or `require_*_action_dep`.
4. Expose in effective permissions (automatic if matrix rows exist).
5. Gate frontend UI with `usePermission` / `hasOrgPermission`.
6. Run `make openapi` and extend frontend types if needed.

---

## Security notes

- Frontend visibility is advisory; always enforce on the backend.
- Catalog tables have no public mutation API.
- Matrix updates require `settings.rbac.update`.
- Policy updates are transactional; cache invalidates immediately after PUT.
- Single-org deployment: all policy data applies to the one organization.

---

## Testing

| Suite | Location | Notes |
|-------|----------|-------|
| Matrix unit tests | `backend/tests/rbac/test_checker.py` | Default policy semantics |
| Integration tests | `backend/tests/rbac/test_rbac_integration.py` | Requires Postgres (`pytest -m integration`) |
| API tests | `backend/tests/api/test_*.py` | Mock `require_permission` where DB matrix unavailable |

Run migrations before integration tests:

```bash
make migrate
cd backend && uv run pytest -m integration tests/rbac/
```

---

## Known limitations (as-built)

- `users.is_org_admin` still exists on `UserResponse` and is synced from RBAC; some display logic uses it directly (e.g. user list badges).
- `require_org_admin_user` remains in `auth/dependencies.py` for legacy callers but protected routes use action-based deps.
- Permission matrix UI edits **team scope only**; org/settings/user policy is migration-defined.
- Audit coverage is partial (matrix + org role changes only).
- `GET /settings/llm-providers` list is open to any authenticated user; mutations require `settings.llm.update`.

---

## Quick reference

```
Principal + org role + (optional) team role
    → PermissionChecker(action, team_id?)
        → lookup rbac_role_permissions
            → allow / 403 Permission denied
```

**Admin UI:** `/settings/permissions`
**User org role:** `PUT /api/v1/users/{id}/organization-role`
**Effective permissions:** `GET /api/v1/auth/me` → `permissions`
**Code entry point:** `backend/app/rbac/checker.py`
