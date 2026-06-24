---
name: dockerfile-builder
description: >-
  Generate production-ready multi-stage Dockerfiles for Python (uv), Vite React
  SPAs, Next.js, and Python+Vite bundled monorepos. Use when the user asks to
  write, create, or optimize a Dockerfile, containerize an app, dockerize a
  project, or mentions Docker + uv, Vite, React, Next.js, nginx static hosting,
  or multi-stage builds. This SKILL.md is an index — read the matching reference
  and copy from assets/ before generating.
license: MIT
compatibility: Requires Docker BuildKit for cache mounts. Python projects need uv (pyproject.toml + uv.lock). Next.js needs output standalone.
metadata:
  author: Nguyen Khac Thanh - <ask@nkthanh.dev>
  version: "0.1.0"
---

# Dockerfile Builder

Opinionated, production-ready Dockerfiles for four project types. This file is an
**index** — read the linked reference for the chosen type, then start from the
matching template in `assets/`.

> **Read [references/common.md](references/common.md) first.** It defines build
> metadata (`VERSION`, OCI labels), multi-stage principles, security defaults,
> caching, and the required `.dockerignore` companion file.

## When to apply

Use this skill when the user wants to:

- Create a new `Dockerfile` for their project
- Containerize or dockerize an application
- Optimize an existing Dockerfile for smaller images or faster builds
- Set up nginx static hosting for a Vite/React SPA
- Bundle a Python backend with a Vite frontend in one image

## Pick the project type

| Type | Signals in the repo | Reference | Template |
| --- | --- | --- | --- |
| **python** | `pyproject.toml` + `uv.lock`, Python service/CLI | [references/python.md](references/python.md) | [assets/python.Dockerfile](assets/python.Dockerfile) |
| **vite-react** | Vite + React, `dist/` static output, no SSR | [references/vite-react.md](references/vite-react.md) | [assets/vite-react.Dockerfile](assets/vite-react.Dockerfile) |
| **nextjs** | `next` dependency, SSR/API routes/Server Actions | [references/nextjs.md](references/nextjs.md) | [assets/nextjs.Dockerfile](assets/nextjs.Dockerfile) |
| **python-vite-react-bundler** | `backend/` (uv) + `frontend/` (Vite), single container | [references/python-vite-react-bundler.md](references/python-vite-react-bundler.md) | [assets/python-vite-react-bundler.Dockerfile](assets/python-vite-react-bundler.Dockerfile) |

Shared template for all types: [assets/dockerignore](assets/dockerignore) → copy to `.dockerignore`.

If the type is unclear, inspect the repo (`pyproject.toml`, `package.json`,
`next.config.*`, directory layout) and ask the user to confirm before writing.

## Workflow

1. Read [references/common.md](references/common.md).
2. Open the reference and template for the identified project type.
3. Inspect the user's project: entry points, ports, monorepo paths, lockfiles,
   existing `nginx.conf` or `next.config`.
4. Copy the template to the project root (or appropriate directory) and adapt:
   - `CMD` / entry point
   - `EXPOSE` port
   - `WORKDIR` and `COPY` paths for monorepos
   - `IMAGE_TITLE`, `IMAGE_AUTHORS`
   - Build-time env vars (`VITE_*`, `NEXT_PUBLIC_*`)
5. Copy [assets/dockerignore](assets/dockerignore) to `.dockerignore` at the build
   context root; remove sections that do not apply (see [common.md](references/common.md)).
6. For **nextjs**: ensure `output: "standalone"` in `next.config`.
7. For **vite-react**: copy [assets/nginx-spa.conf](assets/nginx-spa.conf) next
   to the Dockerfile (or use the project's nginx config).
8. Provide the `docker build` command with `--build-arg` for version metadata.

## Technical requirements (non-negotiable)

1. **Multi-stage builds** — separate deps, build, and runtime stages.
2. **Minimal final image** — no compilers, uv, or Node in the runner unless
   required at runtime.
3. **SPA (vite-react)** — final stage uses **nginx** to serve `dist/`.
4. **Build provenance** — every Dockerfile includes `VERSION`, `BUILD_DATE`,
   `VCS_REF`, and OCI `LABEL`s (see common reference).
5. **Simplicity** — prefer readable steps over clever shell; comment only where
   the reason is not obvious.

## Quick comparison

| Type | Final base | Runtime | Typical port |
| --- | --- | --- | --- |
| python | `python:*-slim` | `.venv` entrypoint | 8000 |
| vite-react | `nginx:alpine` | static files | 80 |
| nextjs | `node:*-slim` | `node server.js` (standalone) | 3000 |
| python-vite-react-bundler | `python:*-slim` | API + `/app/static` | 8000 |

## External references

- [uv — Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/)
- [uv-docker-example](https://github.com/astral-sh/uv-docker-example)
- [Next.js with-docker example](https://github.com/vercel/next.js/tree/canary/examples/with-docker)
- [Agent Skills specification](https://agentskills.io/specification)
