---
description: Shared Dockerfile conventions for all project types — build metadata, labels, multi-stage principles, and .dockerignore.
---

# Common Dockerfile Conventions

Apply these rules to **every** Dockerfile produced by this skill, regardless of
project type.

## Design principles

1. **Multi-stage by default.** Separate dependency install, compile/build, and
   runtime into distinct stages. Only copy artifacts needed at runtime into the
   final image.
2. **Minimize final image size.** Use slim/alpine bases where appropriate; do not
   copy build tools, source code, or caches into the runner stage unless
   required at runtime.
3. **Keep Dockerfiles readable.** Prefer clear stage names, short comments that
   explain *why*, and straight-line steps over clever shell one-liners.
4. **Pin tool versions.** Pin base image tags, `uv`, and Node versions via `ARG`
   at the top so upgrades are a single-line change.

## Build metadata (required)

Every Dockerfile must declare build arguments and OCI labels so the image carries
provenance for the build that produced it.

```dockerfile
# syntax=docker/dockerfile:1

# --- Build metadata (set via --build-arg or CI) ---
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS="Your Name <you@example.com>"

LABEL org.opencontainers.image.title="my-app" \
      org.opencontainers.image.description="Short description of the service" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.authors="${IMAGE_AUTHORS}"
```

**CI build example:**

```bash
docker build \
  --build-arg VERSION="$(git describe --tags --always)" \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
  --build-arg IMAGE_AUTHORS="Your Name <you@example.com>" \
  -t my-app:latest .
```

Re-declare `ARG VERSION` (and any other args used in `ENV` or `RUN`) in each
stage that needs them — `ARG` scope does not carry across `FROM` lines.

Embed the version in the application when the stack supports it:

| Stack | Mechanism |
| --- | --- |
| Vite | `ARG VITE_APP_VERSION` → `ENV VITE_APP_VERSION=$VITE_APP_VERSION` before `npm run build` |
| Next.js | `ARG NEXT_PUBLIC_APP_VERSION` before `npm run build` |
| Python | `ENV APP_VERSION=$VERSION` in the runner stage |

## Multi-stage naming

Use descriptive stage aliases:

| Stage alias | Purpose |
| --- | --- |
| `dependencies` | Install lockfile deps only (maximizes layer cache) |
| `builder` | Compile / build application artifacts |
| `runner` | Minimal production runtime |

For SPA apps served by nginx, the final stage is typically `runner` based on
`nginx:alpine`.

## Security defaults

- Run as a **non-root** user in the final stage when the base image allows it.
- Set `ENV PYTHONUNBUFFERED=1` for Python services.
- Set `ENV NODE_ENV=production` for Node build and runtime stages.
- Do not install dev dependencies in production images.

## Caching

Use BuildKit cache mounts for package managers:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
```

```dockerfile
RUN --mount=type=cache,target=/root/.npm \
    npm ci
```

Enable BuildKit: `DOCKER_BUILDKIT=1 docker build ...`

## `.dockerignore` (required companion file)

Always create or update `.dockerignore` at the **Docker build context root**
(alongside or above the `Dockerfile`). Start from the skill template:

**[assets/dockerignore](../assets/dockerignore)** → copy to `.dockerignore` in the
project, then remove sections that do not apply.

| Project type | Required sections in `.dockerignore` |
| --- | --- |
| python | Version control, Python/uv, Environment, IDE |
| vite-react | Version control, Node/frontend, Environment, IDE |
| nextjs | Version control, Node/frontend, Environment, IDE |
| python-vite-react-bundler | All of the above (`**/` patterns cover monorepos) |

**Critical rules:**

- **`.venv` must be ignored** (use `**/.venv` in monorepos) — the virtualenv is
  platform-specific and must be created inside the image. See
  [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/).
- **`node_modules`, `dist`, `.next`, `out` must be ignored** — rebuilt in the
  image; copying from the host breaks reproducibility and busts layer cache.
- **Never include `.env` files** with secrets — pass runtime config via
  orchestrator env vars or mounted secrets.

## Workflow checklist

When writing a Dockerfile for a user project:

1. Identify the project type (see `SKILL.md` index).
2. Read the matching `references/<type>.md`.
3. Start from `assets/<type>.Dockerfile` and adapt paths, commands, and ports to
   the actual project.
4. Apply the build metadata block from this file.
5. Copy [assets/dockerignore](../assets/dockerignore) to `.dockerignore` and trim
   unused sections.
6. Tell the user any required config changes (e.g. `output: "standalone"` for
   Next.js).

## References

- [Agent Skills specification](https://agentskills.io/specification)
- [uv — Using uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/)
- [OCI image annotations](https://github.com/opencontainers/image-spec/blob/main/annotations.md)
