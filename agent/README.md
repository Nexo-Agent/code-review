# Nexo Co-Review Agent

OpenCode runtime and MCP server (`coreview-git_*`, `coreview-ci_*`) for PR reviews.

Review skills for OpenCode live in `skills/` and are copied into the image at `/opencode/skills/`.

```bash
cd agent && uv sync
uv run coreview-agent serve --transport sse --host 0.0.0.0 --port 8001
```

Docker image (OpenCode + MCP + git):

```bash
make build-agent   # from repo root
```
