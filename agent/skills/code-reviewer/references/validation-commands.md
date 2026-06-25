# Validation commands during review

Use the **bash** tool in the cloned repository workspace (`--dir` session root) to
run project checks. Prefer evidence from real command output over guessing.

## Discover commands (in order)

1. **`AGENTS.md`** / **`CONTRIBUTING.md`** — project-specific lint/test commands
2. **`README.md`** — setup and verify sections
3. **`Makefile`** — targets like `lint`, `test`, `test-unit`, `typecheck`
4. **`package.json`** — `scripts.lint`, `scripts.typecheck`, `scripts.test`
5. **`pyproject.toml`** — `[tool.uv]`, pytest/ruff config; infer `uv run` commands
6. **`.github/workflows/*.yml`** — CI steps (copy the same commands locally)
7. **Language defaults** (only if nothing above exists):
   - Python: `uv run ruff check .`, `uv run pytest` (or `python -m pytest`)
   - Node/TS: `npm run lint`, `npm run typecheck`, `npm test`
   - Go: `go test ./...`, `go vet ./...`
   - Rust: `cargo test`, `cargo clippy`

## Install dependencies (when needed)

Run non-interactive installs before validation if lockfiles exist:

| Stack | Command |
|-------|---------|
| uv workspace | `uv sync --frozen` or `uv sync` |
| npm | `npm ci` or `npm install` |
| yarn | `corepack enable && yarn install --immutable` or `yarn install` |
| pnpm | `corepack enable && pnpm install --frozen-lockfile` |

Skip install if `node_modules/` or `.venv/` already exists. If install fails
(network, missing tool), note it in an **info** finding and continue static review.

## What to run

**Minimum (always attempt):**

- Lint / formatter check for changed languages
- Typecheck (TypeScript, mypy, pyright, etc.) when the project uses it
- Unit tests — prefer **targeted** scope first:
  - Python: `uv run pytest path/to/test_file.py -q`
  - JS: `npm test -- --runTestsByPath path/to/test` or package-specific pattern

**Full suite** — only when fast (`make test-unit`, small repo) or when change
touches shared infrastructure (CI, build, migrations).

## Time budget

Review runs are unattended with a finite timeout. Prefer:

1. Targeted tests for changed modules
2. Lint + typecheck on changed paths when supported
3. Full `make test` only if steps 1–2 pass quickly

## Using results in findings

- **Failing lint/typecheck/test** → usually **warning** or **critical** with
  command, exit code, and relevant stderr excerpt in **Problem**
- **Passing checks** → strengthens confidence; do not add findings solely for LGTM
- **Could not run** (missing tool/deps) → **info** finding explaining the gap

## Safety

- Read-only review: do **not** modify source files, commit, or push
- Do **not** run destructive commands (`rm -rf`, `docker system prune`, deploy)
- Do **not** start long-running servers; use test/lint targets only
- Stay inside the cloned repo directory
