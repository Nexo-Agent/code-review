# Agent Executor

## Purpose

The agent executor is the isolated runtime that runs a single review session for one pull request or merge request revision.

Its responsibilities are:

- receive review context through environment variables
- clone or reuse the target repository workspace
- run OpenCode with the bundled review skill
- publish inline comments and summary comments back to the Git provider
- send lifecycle callbacks and findings back to the backend

It is intentionally separated from the main application so review execution can remain ephemeral, isolated, and replaceable.

## Current implementation

The current implementation lives in the `agent/` package and is shipped as a dedicated container image.

- CLI entrypoint: `cogito-review-agent review run --review-id <uuid>`
- Main execution flow: `agent/app/services/review_runner.py`
- Callback client: `agent/app/services/review_callback.py`
- MCP server: `agent/app/mcp/server.py`
- Bundled review skill: `agent/skills/code-reviewer/`

The backend worker spawns the agent as a one-shot container for each review run.

## Runtime model

The executor is designed as a stateless one-shot process.

- One container handles one review run.
- The container exits when the review completes or fails.
- No application database connection is opened from the agent.
- Persistent state is externalized through mounted workspace volumes and callback events.

This means the agent can be replaced, retried, or scaled independently from the backend API.

## Inputs

The executor is configured entirely through environment variables prepared by the backend worker.

Core inputs include:

- review identity: `COGITO_REVIEW_REVIEW_ID`
- repository identity: `COGITO_REVIEW_REPO_FULL_NAME`
- PR or MR number: `COGITO_REVIEW_PR_NUMBER`
- target commit SHA: `COGITO_REVIEW_HEAD_SHA`
- Git provider selection and credentials
- LLM provider selection and credentials
- callback endpoint and HMAC secret
- workspace root and OpenCode runtime settings
- optional repository-specific system prompt

The environment is assembled in `backend/app/services/review_job_prepare.py`.

## Outputs

The executor reports results through callback events only.

- callback endpoint: `POST /api/v1/agent/review-events`
- payload schema: `shared/coreview_shared/schemas/review-callback-v1.schema.json`
- authentication: HMAC SHA-256 via `X-Review-Signature-256`

Supported lifecycle events:

- `review.started`
- `review.completed`
- `review.failed`

`review.completed` includes the normalized findings and delivery stats such as whether summary and inline comments were posted.

## Isolation boundaries

The executor is intentionally constrained.

- It does not read or write PostgreSQL directly.
- It does not own review state transitions.
- It does not make authorization decisions.
- It only receives the minimum review configuration required for one run.

The backend remains the source of truth for review records, permissions, users, teams, and integrations.

## Workspace behavior

The executor uses a mounted workspace root, typically `/workspaces`.

Current workspace strategy:

- a shared bare mirror is kept per repository
- a per-review worktree is created for the target PR or MR revision
- the worktree is cleaned up after the run

This keeps git operations fast while preserving isolation between review runs.

## LLM execution model

The executor currently runs OpenCode in headless CLI mode.

- command builder: `shared/coreview_shared/llm/opencode.py`
- generated config materialization: `agent/app/services/opencode_config.py`
- bundled agent id: `code-reviewer`

OpenCode receives a prepared review prompt and returns structured findings in JSON form.

## MCP toolbase

The agent image includes a local MCP server that exposes helper tools for the review session.

Current tool categories:

- Git inspection tools
- CI summary tools

The MCP server is started as a stdio subprocess inside the container, not as a standalone network service.

## Supported deployment relationship

Today the executor is primarily used by the Docker runtime path:

- worker prepares a review job
- runtime provider spawns the agent container
- agent calls back into the backend API

The runtime abstraction also includes a Kubernetes provider, but Kubernetes review execution is not implemented yet.
