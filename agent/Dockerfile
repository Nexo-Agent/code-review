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

WORKDIR /workspace

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./
COPY shared/ shared/
COPY backend/pyproject.toml backend/README.md ./backend/
COPY ${AGENT_DIR}/pyproject.toml ${AGENT_DIR}/README.md ./${AGENT_DIR}/

WORKDIR /workspace/${AGENT_DIR}

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

COPY shared/ /workspace/shared/
COPY ${AGENT_DIR}/ /workspace/${AGENT_DIR}/

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
      org.opencontainers.image.description="Nexo Co-Review agent — OpenCode CLI review runner with bundled MCP and git" \
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
    libgcc \
    make \
    nodejs \
    npm

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/

COPY --from=opencode-base /usr/local/bin/opencode /usr/local/bin/opencode

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    APP_VERSION=${VERSION} \
    PATH="/app/.venv/bin:$PATH" \
    OPENCODE_CONFIG=/config/opencode.json \
    NEXO_COREVIEW_WORKSPACE_ROOT=/workspaces

COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /workspace/agent/app /app/app
COPY --from=python-builder /workspace/agent/pyproject.toml /app/pyproject.toml

COPY agent/docker/agent-entrypoint.sh /usr/local/bin/agent-entrypoint.sh
COPY agent/docker/opencode.agent.json /config/opencode.json
COPY agent/skills/ /opencode/skills/

RUN chmod +x /usr/local/bin/agent-entrypoint.sh \
 && mkdir -p /workspaces

VOLUME ["/workspaces", "/config"]

ENTRYPOINT ["/usr/local/bin/agent-entrypoint.sh"]
