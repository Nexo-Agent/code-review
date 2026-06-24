---
description: Dockerfile guide for Python projects managed with uv — multi-stage build, dependency caching, and minimal runtime image.
---

# Python (uv) Dockerfile

Use this reference when the project is a **Python application managed with uv**
(`pyproject.toml` + `uv.lock` at the project root or in a known subdirectory).

Template: [assets/python.Dockerfile](../assets/python.Dockerfile)

## When to use

- FastAPI, Flask, Django, CLI tools, workers, or any Python service using uv.
- Project has `pyproject.toml` and preferably a committed `uv.lock`.

## Architecture

Two-stage build following
[uv's non-editable install pattern](https://docs.astral.sh/uv/guides/integration/docker/#non-editable-installs):

```
builder (python slim + uv)  →  install deps + project into .venv
runner  (python slim)       →  copy .venv only, run app entrypoint
```

The runner stage does **not** include uv, source code, or build caches — only the
virtual environment with a non-editable install.

## Key uv settings

| Variable | Value | Why |
| --- | --- | --- |
| `UV_COMPILE_BYTECODE` | `1` | Faster cold starts in production |
| `UV_LINK_MODE` | `copy` | Required when using cache mounts |
| `UV_NO_DEV` | `1` | Omit dev dependencies |
| `UV_PYTHON_DOWNLOADS` | `0` | Use the base image's Python; avoid extra downloads |

Install uv by copying the binary from the official distroless image (pin the
version):

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/
```

## Layer caching strategy

1. Copy only `pyproject.toml` + `uv.lock` (bind-mount in `RUN`).
2. `uv sync --locked --no-install-project --no-editable` — installs transitive deps.
3. `COPY` application source.
4. `uv sync --locked --no-editable` — installs the project itself.

This mirrors the [intermediate layers](https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers)
optimization from the uv docs.

## Entrypoint

Prefer invoking the installed console script directly from `.venv`:

```dockerfile
CMD ["/app/.venv/bin/my-app"]
```

Or set `PATH` and use a module:

```dockerfile
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "my_app"]
```

Adapt to the project's actual entry point (`pyproject.toml` `[project.scripts]` or
documented run command).

## Customization points

| Placeholder | Default | Change when |
| --- | --- | --- |
| `PYTHON_VERSION` | `3.12` | Project requires a different Python |
| `UV_VERSION` | `0.11.21` | Pin to match local uv |
| `WORKDIR` | `/app` | Monorepo with backend in a subdirectory |
| `CMD` | `uvicorn` example | Match the actual ASGI/WSGI/CLI entry |

## Monorepo / subdirectory

If `pyproject.toml` lives in `backend/`:

- Set `WORKDIR /app/backend`
- Adjust `COPY` paths for lockfile bind mounts
- Keep `.dockerignore` at the **build context root** (usually repo root)

## Workspace projects

For uv workspaces, use `--no-install-workspace` in the first sync and `--frozen`
instead of `--locked` until all workspace members are copied. See
[uv workspace Docker docs](https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers-in-workspaces).

## Verification

```bash
docker build -t my-app .
docker run --rm -p 8000:8000 my-app
```

Confirm the service starts, health endpoint responds, and `docker inspect`
shows the OCI labels from [common.md](common.md).
