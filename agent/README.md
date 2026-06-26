# Cogito Review Agent

OpenCode CLI review runner with bundled MCP tools (`coreview-git_*`, `coreview-ci_*`).

Each review runs as a one-shot container:

```bash
cogito-review-agent review run --review-id <uuid>
```

Inside the container, `opencode run` reads the review prompt from **stdin**. With `--print-logs` and `--log-level`, internal OpenCode logs stream to **stderr** in real time; `--format json` emits NDJSON events on **stdout**. The Python wrapper streams both pipes to container stdout so the worker can follow progress via `docker logs`.

MCP tools are started as a local stdio subprocess (`cogito-review-agent serve`), not as an HTTP server.

Review skills for OpenCode live in `skills/code-reviewer/` and are copied into the
image at `/opencode/skills/`. The skill name matches the OpenCode agent id
(`code-reviewer`).

## Callback-only reporting

The agent is **callback-only**: it does not connect to Postgres. The orchestrator injects:

| Env | Purpose |
|-----|---------|
| `COGITO_REVIEW_CALLBACK_URL` | POST target for review events |
| `COGITO_REVIEW_CALLBACK_SECRET` | HMAC secret (`X-Review-Signature-256`) |
| `COGITO_REVIEW_CALLBACK_METADATA` | Opaque JSON passthrough (e.g. `delivery_id`) |

Events follow **review-callback-v1** — see [`shared/coreview_shared/schemas/review-callback-v1.schema.json`](../shared/coreview_shared/schemas/review-callback-v1.schema.json).

### Standalone deployment

```bash
docker run --rm \
  -e COGITO_REVIEW_CALLBACK_URL=https://my-orchestrator.example/hooks/review \
  -e COGITO_REVIEW_CALLBACK_SECRET=shared-secret \
  -e COGITO_REVIEW_REVIEW_ID=$(uuidgen) \
  -e COGITO_REVIEW_REPO_FULL_NAME=org/repo \
  -e COGITO_REVIEW_PR_NUMBER=42 \
  -e COGITO_REVIEW_HEAD_SHA=abc123 \
  -e COGITO_REVIEW_GITHUB_TOKEN=ghp_... \
  -e COGITO_REVIEW_LLM_PROVIDER_ID=openai-compat \
  -e COGITO_REVIEW_LLM_BASE_URL=https://api.openai.com/v1 \
  -e COGITO_REVIEW_LLM_API_TOKEN=sk-... \
  -e COGITO_REVIEW_LLM_MODEL=gpt-4o \
  -e COGITO_REVIEW_OPENCODE_MODEL=openai-compat/gpt-4o \
  cogito-review-agent:dev \
  cogito-review-agent review run --review-id <same-uuid>
```

Implement `POST` + HMAC verify on your side; no Cogito Review database required.

## Local dev

```bash
cd agent && uv sync
uv run cogito-review-agent review run --review-id <uuid>
```

Docker image (OpenCode + MCP + git):

Built automatically on `make dev` / `make prod-up`, or manually:

```bash
make build-agent   # docker build -f agent/Dockerfile -t cogito-review-agent:dev .
```
