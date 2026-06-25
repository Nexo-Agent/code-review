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

WORKDIR /workspace

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/workspace/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY shared/ shared/
COPY backend/pyproject.toml backend/README.md ./backend/
COPY agent/pyproject.toml agent/README.md ./agent/

WORKDIR /workspace/${BACKEND_DIR}

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups --no-install-project

COPY shared/ /workspace/shared/
COPY ${BACKEND_DIR}/ /workspace/${BACKEND_DIR}/
COPY docker/dev-api-entrypoint.sh /usr/local/bin/dev-api-entrypoint.sh

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups \
 && chmod +x /usr/local/bin/dev-api-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/dev-api-entrypoint.sh"]
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--reload", "--reload-dir", "app", "--reload-dir", "/workspace/shared/coreview_shared", "--host", "0.0.0.0", "--port", "8000"]

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

WORKDIR /workspace

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/workspace/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY shared/ shared/
COPY backend/pyproject.toml backend/README.md ./backend/
COPY ${AGENT_DIR}/pyproject.toml ${AGENT_DIR}/README.md ./${AGENT_DIR}/

WORKDIR /workspace/${AGENT_DIR}

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups --no-install-project

COPY shared/ /workspace/shared/
COPY ${AGENT_DIR}/ /workspace/${AGENT_DIR}/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-groups

EXPOSE 8001

CMD ["uv", "run", "coreview-agent", "serve", "--transport", "sse", "--host", "0.0.0.0", "--port", "8001"]
