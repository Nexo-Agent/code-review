# Nexo Co-Review

[![CI](https://github.com/Nexo-Agent/code-review/actions/workflows/ci.yml/badge.svg)](https://github.com/Nexo-Agent/code-review/actions/workflows/ci.yml)
[![Publish](https://github.com/Nexo-Agent/code-review/actions/workflows/publish.yml/badge.svg)](https://github.com/Nexo-Agent/code-review/actions/workflows/publish.yml)
[![Backend](https://img.shields.io/badge/ghcr.io-nexo--coreview-2496ED?logo=docker&logoColor=white)](https://github.com/Nexo-Agent/code-review/pkgs/container/nexo-coreview)
[![Agent](https://img.shields.io/badge/ghcr.io-nexo--coreview--agent-2496ED?logo=docker&logoColor=white)](https://github.com/Nexo-Agent/code-review/pkgs/container/nexo-coreview-agent)

Codename: `nexo-coreview`

AI-powered pull request reviews for GitHub. Connect a repository, point a webhook at this service, and get structured findings on every PR — powered by [OpenCode](https://opencode.ai/) and the LLM provider you choose.

## Features

- **Automatic PR reviews** — Triggered on `opened`, `synchronize`, and `reopened` events via GitHub webhooks
- **Structured findings** — Severity, file, line range, title, and description — browsable in the web UI
- **Multiple LLM providers** — OpenAI-compatible endpoints; configure several profiles and override per repository
- **Per-repo configuration** — Webhook secret, GitHub token, and optional LLM override for each repo (or a catch-all default)
- **Ephemeral agent containers** — Each review spawns an OpenCode + MCP agent via Docker socket; no pre-provisioned agent pool
- **Isolated git workspaces** — Repo clone and review run inside the per-review agent container
- **MCP toolbase** — Agent can inspect git history and CI status through Nexo Co-Review MCP tools (`nexo-coreview`)
- **Self-hosted** — Single Docker image ships the API and web UI together

## Quick start

**Requirements:** Docker and Docker Compose. Copy `docker-compose.yaml` and `.env.example` to your server (or clone the repo).

```bash
cp .env.example .env
# Edit .env: set NEXO_COREVIEW_AGENT_CALLBACK_SECRET and pin image tags if needed
docker compose -f docker-compose.yaml pull
docker compose -f docker-compose.yaml up -d
```

Or from a full clone: `make prod-up`.

Open the app (default port from `APP_PORT`, usually `8000`). Go to **Settings** to add an LLM provider and register your GitHub repository.

### Container images (GHCR)

Published on every push to `main` and on version tags (`v*`):

```bash
docker pull ghcr.io/nexo-agent/nexo-coreview:latest
docker pull ghcr.io/nexo-agent/nexo-coreview-agent:latest
```

Set in `.env` for production (defaults in `.env.example`):

```bash
NEXO_COREVIEW_IMAGE=ghcr.io/nexo-agent/nexo-coreview:latest
NEXO_COREVIEW_AGENT_IMAGE=ghcr.io/nexo-agent/nexo-coreview-agent:latest
```

Use a pinned digest or semver tag in production instead of `latest`.

For local development with hot reload, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Usage

### 1. Configure LLM providers

In **Settings → LLM Providers**, add one or more OpenAI-compatible profiles (base URL, API token, model). The first provider is used by default unless a repository specifies otherwise.

### 2. Register a repository

In **Settings → Repositories**, add the GitHub repo (`owner/name`), webhook secret, and a personal access token with repo access. Leave `repo_full_name` empty to use the entry as a catch-all for unlisted repos.

### 3. Add the GitHub webhook

In your GitHub repository settings, create a webhook:

| Field | Value |
|-------|-------|
| Payload URL | `https://<your-host>/api/v1/webhooks/github` |
| Content type | `application/json` |
| Secret | Same value as in Settings |
| Events | Pull requests |

### 4. Open a pull request

When a PR is opened or updated, a review job is queued. Track progress on the **Reviews** page; findings appear when the run completes.

## Architecture

High-level diagrams: [`docs/architecture.svg`](docs/architecture.svg), [`docs/flow.svg`](docs/flow.svg).

```
GitHub PR event → API webhook → Celery worker → spawn agent container → OpenCode review → findings → Postgres → Web UI
```

## Documentation

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, environment variables, testing |
| [RELEASING.md](RELEASING.md) | Git flow, releases, GHCR publish |
| [AGENTS.md](AGENTS.md) | Instructions for AI coding agents |
| [`.env.example`](.env.example) | Infrastructure environment template |
