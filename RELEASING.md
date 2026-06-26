# Releasing

This document describes the Git workflow, pull request process, and how versioned releases reach [GHCR](https://ghcr.io/cogitoforge-ai/cogito-review).

For day-to-day development setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Branch model

```
main ─────────────────────────────► production releases (GHCR publish)
  ▲
  │ merge when ready to release
  │
dev ─── feature/xyz ─── feature/abc ─── integration & CI
```

| Branch | Purpose | CI | Publish to GHCR |
|--------|---------|----|-----------------|
| `main` | Production-ready code | Yes | Yes (`latest`, `sha-*`) |
| `dev` | Integration / staging | Yes | No |
| `feature/*`, `fix/*`, … | Short-lived topic branches | Yes (via PR) | No |
| Tag `v*` (on `main`) | Semver release | Yes | Yes (`v1.2.3`, `1.2.3`, `sha-*`) |

**Rules**

- `main` is always deployable.
- Day-to-day work merges into `dev` first.
- Only maintainers merge `dev` → `main` for a release.
- Release tags are created on commits that live on `main`.
- Do not force-push `main` or rewrite published tags.

## Daily development

### 1. Start from `dev`

```bash
git fetch origin
git checkout dev
git pull origin dev
git checkout -b feature/my-change
```

Use a short, descriptive branch prefix:

- `feature/` — new capability
- `fix/` — bug fix
- `refactor/` — internal change, no user-visible behaviour
- `chore/` — tooling, deps, CI

### 2. Develop and verify locally

```bash
make lint
make test-unit
# If you touched DB code or migrations:
make test
```

Run the stack when you need end-to-end validation:

```bash
make dev
```

### 3. Commit

- One logical change per commit when practical.
- Message style: imperative, explain **why** (e.g. `fix webhook signature check for repo integrations`).
- Never commit `.env`, tokens, or secrets.

### 4. Push and open a PR

Target branch: **`dev`** (default integration branch).

```bash
git push -u origin feature/my-change
gh pr create --base dev --title "Short summary" --body "$(cat <<'EOF'
## Summary
- …

## Test plan
- [ ] `make lint`
- [ ] `make test-unit`
- [ ] …
EOF
)"
```

## Pull request checklist

Before requesting review:

1. `make lint` passes
2. `make test-unit` passes
3. `make test` if you changed repositories, migrations, or API integration behaviour
4. `make openapi` if HTTP contracts changed
5. New migrations apply cleanly: `make migrate`
6. PR description includes **Summary** and **Test plan**

### What CI runs on the PR

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

| Job | Scope |
|-----|--------|
| Backend lint & test | Ruff, pytest (unit) |
| Agent lint & test | Ruff, pytest |
| Frontend lint & typecheck | ESLint, `tsc` |
| Integration tests | Postgres + dbmate migrate + pytest `-m integration` |
| Docker build (verify) | Builds `cogito-review` and `cogito-review-agent` without pushing |

All jobs must pass before merge.

### Review and merge

1. Address review comments; push new commits to the same branch (CI re-runs).
2. Prefer **Squash and merge** for feature branches into `dev` (one clean commit on `dev`).
3. Delete the topic branch after merge.

## Promoting `dev` → `main`

When `dev` is stable and you want a production release:

### 1. Prepare

- Confirm [Actions → CI](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/ci.yml) is green on `dev`.
- Review merged PRs since the last release.
- Note any **database migrations** — production deploy must run `migrate` before or during rollout.
- Note any **breaking config** changes for operators (`.env`, Settings UI).

### 2. Open a release PR

```bash
git fetch origin
git checkout dev
git pull origin dev
gh pr create --base main --head dev --title "Release YYYY-MM-DD" --body "$(cat <<'EOF'
## Summary
Promote dev to main.

## Test plan
- [ ] CI green on dev
- [ ] Migrations reviewed
- [ ] Release notes / tag planned
EOF
)"
```

Use a merge commit or merge commit (not squash) for `dev` → `main` if you want to preserve individual commits; squash is acceptable if `dev` history is already clean.

### 3. Merge to `main`

After the PR merges:

1. **CI** runs on `main`.
2. **Publish** ([`.github/workflows/publish.yml`](.github/workflows/publish.yml)) runs automatically when CI succeeds.
3. Images are pushed to GHCR:

   | Image | Example tags |
   |-------|----------------|
   | `ghcr.io/cogitoforge-ai/cogito-review` | `latest`, `sha-abc1234` |
   | `ghcr.io/cogitoforge-ai/cogito-review-agent` | `latest`, `sha-abc1234` |

Track progress: [Actions → Publish](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/publish.yml).

### 4. Sync `dev` with `main`

After merging `dev` → `main`, fast-forward or merge `main` back into `dev` so both branches align:

```bash
git checkout dev
git pull origin dev
git merge origin/main
git push origin dev
```

## Versioned release (semver tag)

For a named release (recommended for production pin and changelog):

### 1. Ensure `main` is ready

Same checks as promoting `dev` → `main`. The tagged commit must be on `main`.

### 2. Create and push an annotated tag

Use [Semantic Versioning](https://semver.org/): `vMAJOR.MINOR.PATCH`.

```bash
git fetch origin
git checkout main
git pull origin main

# Review commits since last tag
git log "$(git describe --tags --abbrev=0 2>/dev/null || echo '')"..HEAD --oneline

git tag -a v0.2.0 -m "Release v0.2.0: short description"
git push origin v0.2.0
```

### 3. Automated publish

Pushing `v*` triggers **CI**, then **Publish** publishes:

| Tag pushed | GHCR tags (both images) |
|------------|-------------------------|
| `v0.2.0` | `v0.2.0`, `0.2.0`, `sha-<short>` |

`latest` is **not** updated by tag-only pushes (only `main` branch pushes update `latest`).

### 4. GitHub Release (optional)

Create a release from the tag in GitHub UI or with CLI:

```bash
gh release create v0.2.0 --title "v0.2.0" --notes "$(cat <<'EOF'
## Changes
- …
EOF
)"
```

### 5. Production deploy

Pin images by semver or digest — avoid floating `latest` in production.

```bash
# Semver
docker pull ghcr.io/cogitoforge-ai/cogito-review:0.2.0
docker pull ghcr.io/cogitoforge-ai/cogito-review-agent:0.2.0

# Or by commit
docker pull ghcr.io/cogitoforge-ai/cogito-review:sha-abc1234
```

Update `.env` (or your orchestrator):

```bash
COGITO_REVIEW_AGENT_IMAGE=ghcr.io/cogitoforge-ai/cogito-review-agent:0.2.0
```

Deploy with Compose:

```bash
make prod
```

Migrations run automatically via the `migrate` init service on stack bring-up.

## Hotfix flow

Urgent fix needed in production without waiting for unrelated `dev` work:

```bash
git fetch origin
git checkout main
git pull origin main
git checkout -b fix/critical-issue

# fix, test, commit
make lint && make test-unit

git push -u origin fix/critical-issue
gh pr create --base main --title "fix: …" --body "…"
```

After merge to `main`:

1. CI + Publish run (new `latest` and `sha-*`).
2. Tag a patch release if appropriate (`v0.2.1`).
3. **Backport** the fix to `dev`:

```bash
git checkout dev
git pull origin dev
git cherry-pick <hotfix-commit-sha>
git push origin dev
```

## Manual publish

Normally publish is fully automated. To rebuild and push without a new merge:

1. Open [Actions → Publish](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/publish.yml).
2. **Run workflow** → choose branch (usually `main`).

Use sparingly — prefer tag or merge-driven releases for traceability.

## GHCR package visibility

First publish creates packages under the `CogitoForge-AI` org. To allow anonymous `docker pull`:

1. GitHub → **Packages** → `cogito-review` / `cogito-review-agent`
2. **Package settings** → **Change visibility** → **Public**

Private packages require `docker login ghcr.io` for pulls.

Production `.env` should reference the full image path:

```bash
COGITO_REVIEW_AGENT_IMAGE=ghcr.io/cogitoforge-ai/cogito-review-agent:0.2.0
```

## Recommended branch protection

Configure in **Settings → Branches** for `main` (and optionally `dev`):

| Rule | `main` | `dev` |
|------|--------|-------|
| Require PR before merging | Yes | Yes |
| Require status check **CI** | Yes | Yes |
| Require branches up to date | Yes | Recommended |
| Restrict who can push | Maintainers | Maintainers |
| Allow force push | No | No |

## Quick reference

```text
feature/* ──PR──► dev ──PR──► main ──push──► GHCR (latest)
                              │
                              └── tag v* ──► GHCR (semver)
```

| Action | Command / trigger |
|--------|-------------------|
| Local lint & test | `make lint`, `make test-unit`, `make test` |
| Open feature PR | base: `dev` |
| Release to production | merge `dev` → `main` |
| Semver release | `git tag -a vX.Y.Z && git push origin vX.Y.Z` |
| Pull release images | `docker pull ghcr.io/cogitoforge-ai/cogito-review:VERSION` |
| Deploy | `make prod` |

## Related docs

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev environment, env vars, testing |
| [README.md](README.md) | Quick start, GHCR pull commands |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI pipeline |
| [`.github/workflows/publish.yml`](.github/workflows/publish.yml) | Image publish pipeline |
