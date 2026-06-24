---
description: Dockerfile guide for monorepos with a Python (uv) backend and Vite React frontend bundled into a single container image.
---

# Python + Vite React Bundler Dockerfile

Use this reference when a **single container** serves both a Python API and a
pre-built Vite React SPA. Typical layout:

```
project/
├── backend/           # uv Python project (FastAPI, etc.)
│   ├── pyproject.toml
│   ├── uv.lock
│   └── app/
│       └── main.py    # serves /api + static files
└── frontend/          # Vite React SPA
    ├── package.json
    └── src/
```

Template: [assets/python-vite-react-bundler.Dockerfile](../assets/python-vite-react-bundler.Dockerfile)

## When to use

- Python backend serves the built frontend as static files (e.g. `StaticFiles`
  mount at `/` or `/assets`)
- User wants one image, one process — not separate nginx + API containers
- Frontend API calls use relative paths (`/api/...`) proxied by the Python app

## Architecture

Three-stage build:

```
frontend-builder (node)  →  build Vite → dist/
python-builder (uv)      →  uv sync --no-editable → .venv
runner (python slim)     →  .venv + static files, run Python server
```

```
┌─────────────────────────────────────┐
│  runner (python:3.12-slim)          │
│  ├── /app/.venv/                    │
│  └── /app/static/  ← frontend dist  │
│       CMD → uvicorn / gunicorn       │
└─────────────────────────────────────┘
```

## Static files destination

The template copies the Vite build output to `/app/static/`. The Python app must
serve this directory:

**FastAPI example:**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/{full_path:path}")
async def spa(full_path: str):
  # Return index.html for client-side routes
  return FileResponse("static/index.html")
```

Adapt mount paths to match Vite's `base` config and the project's existing static
serving setup.

## Frontend API URL

For bundled deployments, prefer **relative** API URLs in the frontend:

```typescript
const api = import.meta.env.VITE_API_URL ?? "/api";
```

Set `VITE_API_URL=/api` at build time (or omit it) so the same image works behind
any host.

## Customization points

| Placeholder | Default | Change when |
| --- | --- | --- |
| `BACKEND_DIR` | `backend` | Python root is elsewhere |
| `FRONTEND_DIR` | `frontend` | Frontend root is elsewhere |
| `STATIC_DIR` | `/app/static` | Backend expects a different path |
| `CMD` | `uvicorn` example | Match actual ASGI entry |

## Alternative: separate containers

If the user prefers independent scaling or nginx for the SPA, do **not** use this
template — generate separate Dockerfiles using
[python.md](python.md) and [vite-react.md](vite-react.md) plus a
`docker-compose.yaml`.

## Verification

```bash
docker build -t my-bundled-app .
docker run --rm -p 8000:8000 my-bundled-app
```

- `curl http://localhost:8000/` returns the SPA HTML
- `curl http://localhost:8000/api/health` (or equivalent) returns API response
- Client-side navigation works after page load
