# Cogito Review

[![CI](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/ci.yml/badge.svg)](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/ci.yml)
[![Publish](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/publish.yml/badge.svg)](https://github.com/CogitoForge-AI/cogito-review/actions/workflows/publish.yml)
[![Backend](https://img.shields.io/badge/ghcr.io-cogito--review-2496ED?logo=docker&logoColor=white)](https://github.com/CogitoForge-AI/cogito-review/pkgs/container/cogito-review)
[![Agent](https://img.shields.io/badge/ghcr.io-cogito--review--agent-2496ED?logo=docker&logoColor=white)](https://github.com/CogitoForge-AI/cogito-review/pkgs/container/cogito-review-agent)

AI-assisted code review platform for pull requests and merge requests.

Cogito Review helps teams review code faster with automated, structured feedback on pull requests and merge requests. Connect your repository, configure your model provider, and let the system surface findings your reviewers can act on quickly.

## Why teams use Cogito Review

- Review changes automatically when pull requests or merge requests are opened or updated
- Get structured findings with clear severity, location, title, and description
- Keep review history and repository settings in one place
- Choose your own OpenAI-compatible model provider
- Use one system across multiple repositories and teams
- Self-host the product in your own environment

## Features

- Automatic review runs triggered by repository events
- Structured findings that are easy to scan and triage
- Web UI for review history, findings, repository settings, and model setup
- Repository-level integration settings
- Team and access management
- SSO and RBAC support
- Review retry support
- Multi-provider Git integration

## Supported integrations

- Git providers: GitHub, GitLab, Azure DevOps, Bitbucket Cloud, Bitbucket Data Center
- Identity: OIDC, SAML 2.0, and local bootstrap login
- LLM providers: OpenAI-compatible endpoints

## Quick start

### Start the app

```bash
cp .env.example .env
make prod
```

Open the application on `http://localhost:${APP_PORT:-8000}`.

### Set it up

1. Open the web app.
2. Add an LLM provider in `Settings -> LLM Providers`.
3. Add a repository integration in `Settings -> Repositories`.
4. Configure your Git provider webhook to point at the backend.
5. Open or update a pull request or merge request to trigger a review.

### Example GitHub webhook

| Field | Value |
| --- | --- |
| Payload URL | `https://<your-host>/api/v1/webhooks/github` |
| Content type | `application/json` |
| Secret | Match the repository integration secret |
| Events | Pull requests |

## Configuration notes

- Set strong values for `COGITO_REVIEW_SESSION_SECRET`, `COGITO_REVIEW_SECRETS_ENCRYPTION_KEY`, and `COGITO_REVIEW_AGENT_CALLBACK_SECRET` in production
- Prefer pinned image tags or digests over `latest`

## Images

Published container images:

```bash
docker pull ghcr.io/cogitoforge-ai/cogito-review:latest
docker pull ghcr.io/cogitoforge-ai/cogito-review-agent:latest
```

Production deployments should pin a version tag or image digest.

## Documentation

For deeper technical and operational details:

- [Deployment guide](docs/deployment.md)
- [Security model](docs/security.md)
- [RBAC model](docs/rbac.md)
- [Architecture overview](docs/architecture-overview.md)
