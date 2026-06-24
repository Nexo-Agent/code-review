# Nexo Co-Review Agent

OpenCode CLI review runner with bundled MCP tools (`coreview-git_*`, `coreview-ci_*`).

Each review runs as a one-shot container:

```bash
coreview-agent review run --review-id <uuid>
```

Inside the container, `opencode run` reads the review prompt from **stdin**. With `--print-logs` and `--log-level`, internal OpenCode logs stream to **stderr** in real time; `--format json` emits NDJSON events on **stdout**. The Python wrapper streams both pipes to container stdout so the worker can follow progress via `docker logs`.

MCP tools are started as a local stdio subprocess (`coreview-agent serve --transport stdio`), not as HTTP servers.

Review skills for OpenCode live in `skills/` and are copied into the image at `/opencode/skills/`.

## Callback-only reporting

The agent is **callback-only**: it does not connect to Postgres. The orchestrator injects:

| Env | Purpose |
|-----|---------|
| `NEXO_COREVIEW_CALLBACK_URL` | POST target for review events |
| `NEXO_COREVIEW_CALLBACK_SECRET` | HMAC secret (`X-Review-Signature-256`) |
| `NEXO_COREVIEW_CALLBACK_METADATA` | Opaque JSON passthrough (e.g. `delivery_id`) |

Events follow **review-callback-v1** — see [`docs/review-callback-v1.schema.json`](../docs/review-callback-v1.schema.json).

### Standalone (without Nexo)

```bash
docker run --rm \
  -e NEXO_COREVIEW_CALLBACK_URL=https://my-orchestrator.example/hooks/review \
  -e NEXO_COREVIEW_CALLBACK_SECRET=shared-secret \
  -e NEXO_COREVIEW_REVIEW_ID=$(uuidgen) \
  -e NEXO_COREVIEW_REPO_FULL_NAME=org/repo \
  -e NEXO_COREVIEW_PR_NUMBER=42 \
  -e NEXO_COREVIEW_HEAD_SHA=abc123 \
  -e NEXO_COREVIEW_GITHUB_TOKEN=ghp_... \
  -e NEXO_COREVIEW_LLM_PROVIDER_ID=openai-compat \
  -e NEXO_COREVIEW_LLM_BASE_URL=https://api.openai.com/v1 \
  -e NEXO_COREVIEW_LLM_API_TOKEN=sk-... \
  -e NEXO_COREVIEW_LLM_MODEL=gpt-4o \
  -e NEXO_COREVIEW_OPENCODE_MODEL=openai-compat/gpt-4o \
  nexo-coreview-agent:dev \
  coreview-agent review run --review-id <same-uuid>
```

Implement `POST` + HMAC verify on your side; no Nexo database required.

## Local dev

```bash
cd agent && uv sync
uv run coreview-agent review run --review-id <uuid>
```

Docker image (OpenCode + MCP + git):

Built automatically on `make dev` / `make prod-up`, or manually:

```bash
make build-agent   # docker compose build agent-image
```
