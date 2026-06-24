# syntax=docker/dockerfile:1

# Nexo Co-Review agent image — OpenCode + MCP + git in one container.

# --- Build metadata ---
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS="Nexo <ask@nkthanh.dev>"
ARG IMAGE_TITLE="nexo-coreview-agent"

# --- Tool versions ---
ARG PYTHON_VERSION=3.11
ARG UV_VERSION=0.11.21
ARG OPENCODE_IMAGE=ghcr.io/anomalyco/opencode:latest

# --- Monorepo paths ---
ARG AGENT_DIR=agent

FROM ${OPENCODE_IMAGE} AS opencode-base

FROM ghcr.io/astral-sh/uv:${UV_VERSION}-alpine AS uv

# =============================================================================
# Stage: python-builder — agent MCP server (coreview-agent serve)
# =============================================================================
FROM python:${PYTHON_VERSION}-alpine AS python-builder

ARG AGENT_DIR=agent

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

COPY ${AGENT_DIR}/pyproject.toml ${AGENT_DIR}/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

COPY ${AGENT_DIR}/ /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# =============================================================================
# Stage: runner — Python 3.11 + OpenCode binary + git + MCP
# =============================================================================
FROM python:${PYTHON_VERSION}-alpine AS runner

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS
ARG IMAGE_TITLE

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
      org.opencontainers.image.description="Nexo Co-Review agent — OpenCode server with bundled MCP and git" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.authors="${IMAGE_AUTHORS}"

RUN apk add --no-cache \
    git \
    openssh-client \
    ca-certificates \
    wget \
    netcat-openbsd \
    libstdc++ \
    libgcc

COPY --from=opencode-base /usr/local/bin/opencode /usr/local/bin/opencode

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    APP_VERSION=${VERSION} \
    PATH="/app/.venv/bin:$PATH" \
    OPENCODE_CONFIG=/config/opencode.json \
    NEXO_COREVIEW_MCP_BIND_HOST=127.0.0.1 \
    NEXO_COREVIEW_MCP_SERVER_PORT=8001 \
    NEXO_COREVIEW_MCP_SERVER_URL=http://127.0.0.1:8001/sse \
    NEXO_COREVIEW_OPENCODE_BIND_HOST=0.0.0.0 \
    NEXO_COREVIEW_OPENCODE_PORT=4096 \
    NEXO_COREVIEW_WORKSPACE_ROOT=/workspaces

COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/app /app/app
COPY --from=python-builder /app/pyproject.toml /app/pyproject.toml

COPY agent/docker/agent-entrypoint.sh /usr/local/bin/agent-entrypoint.sh
COPY agent/docker/opencode.agent.json /config/opencode.json
COPY agent/skills/ /opencode/skills/

RUN chmod +x /usr/local/bin/agent-entrypoint.sh \
 && mkdir -p /workspaces

EXPOSE 4096 8001

VOLUME ["/workspaces", "/config"]

ENTRYPOINT ["/usr/local/bin/agent-entrypoint.sh"]
