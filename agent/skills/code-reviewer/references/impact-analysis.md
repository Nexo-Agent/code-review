# Impact analysis (blast radius)

Static diff review is not enough. Trace how changed code affects the rest of the
repository before finalizing findings.

## 1. Map the change surface

From the PR diff and MCP context:

- List **changed files** and their roles (API, DB, UI, config, tests)
- Note **deleted/renamed** symbols and public exports
- Flag **migrations**, **env/config**, **CI**, and **dependency** changes as
  high blast-radius

## 2. Trace dependents

For each non-trivial change (new/changed function, type, route, schema, env var):

- **grep** / **glob** for importers, callers, and string references
- Check **tests** that cover or should cover the behavior
- For API changes: search route paths, OpenAPI/schema files, and frontend API
  clients
- For DB migrations: search repositories/models using affected tables/columns

## 3. Cross-layer consistency

Verify aligned changes across layers:

| Change type | Also check |
|-------------|------------|
| Backend API schema | Frontend types, hooks, generated OpenAPI |
| DB migration | Repository queries, Pydantic models, integration tests |
| Shared library | All packages that import the module |
| Auth / permissions | Middleware, tests, admin UI |
| Feature flag / config | Defaults, docs, deployment env |

## 4. Regression signals

Combine static tracing with **validation commands** (see
[validation-commands.md](validation-commands.md)):

- If tests exist for touched modules, run them
- If CI config changed, reason about whether local commands mirror CI
- If only tests changed, ensure they assert real behavior (not snapshot churn)

## 5. Report impact in findings

In **Impact**, state *who/what breaks* beyond the edited lines — callers, users,
deployments, data. In **Recommendation**, point to concrete follow-ups (tests,
call-site updates, migration rollout).
