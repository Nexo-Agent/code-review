# syntax=docker/dockerfile:1

# Multi-stage dev images — select target per service in compose:
#   api: build.target: api
#   web: build.target: web

ARG NODE_VERSION=22-alpine
ARG PYTHON_VERSION=3.11
ARG UV_VERSION=0.11.21
ARG BACKEND_DIR=backend
ARG AGENT_DIR=agent
ARG FRONTEND_DIR=frontend

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# =============================================================================
# Stage: api — Python + uv + uvicorn --reload (source bind-mounted at runtime)
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-trixie AS api

ARG BACKEND_DIR

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:$PATH"

COPY ${BACKEND_DIR}/pyproject.toml ${BACKEND_DIR}/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups --no-install-project

COPY ${BACKEND_DIR}/ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--reload", "--reload-dir", "app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage: web — Node + Vite HMR (source bind-mounted at runtime)
# =============================================================================
FROM node:${NODE_VERSION} AS web

ARG FRONTEND_DIR

WORKDIR /app

COPY ${FRONTEND_DIR}/package.json ${FRONTEND_DIR}/yarn.lock ./

RUN corepack enable yarn && yarn install --frozen-lockfile

COPY ${FRONTEND_DIR}/ ./

EXPOSE 5173

CMD ["yarn", "dev", "--host", "0.0.0.0", "--port", "5173"]

# =============================================================================
# Stage: agent — Python + uv (source bind-mounted at runtime)
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-trixie AS agent

ARG AGENT_DIR=agent

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:$PATH"

COPY ${AGENT_DIR}/pyproject.toml ${AGENT_DIR}/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups --no-install-project

COPY ${AGENT_DIR}/ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups

EXPOSE 8001

CMD ["uv", "run", "coreview-agent", "serve", "--transport", "sse", "--host", "0.0.0.0", "--port", "8001"]
