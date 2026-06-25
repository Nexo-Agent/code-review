# syntax=docker/dockerfile:1

# --- Build metadata ---
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS="Nexo <ask@nkthanh.dev>"
ARG IMAGE_TITLE="nexo-coreview"

# --- Tool versions ---
ARG NODE_VERSION=22-alpine
ARG PYTHON_VERSION=3.11
ARG UV_VERSION=0.11.21

# --- Monorepo paths ---
ARG BACKEND_DIR=backend
ARG FRONTEND_DIR=frontend

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# =============================================================================
# Stage: frontend-builder — build Vite React SPA
# =============================================================================
FROM node:${NODE_VERSION} AS frontend-builder

ARG FRONTEND_DIR
ARG VERSION
ARG VITE_API_URL=/api/v1
ARG VITE_APP_VERSION=${VERSION}

WORKDIR /app

COPY ${FRONTEND_DIR}/package.json ${FRONTEND_DIR}/yarn.lock* ${FRONTEND_DIR}/package-lock.json* ${FRONTEND_DIR}/pnpm-lock.yaml* ./

RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/usr/local/share/.cache/yarn \
    --mount=type=cache,target=/root/.local/share/pnpm/store \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
    elif [ -f yarn.lock ]; then \
      corepack enable yarn && yarn install --frozen-lockfile; \
    elif [ -f pnpm-lock.yaml ]; then \
      corepack enable pnpm && pnpm install --frozen-lockfile; \
    else \
      echo "No lockfile found." && exit 1; \
    fi

COPY ${FRONTEND_DIR}/ ./

ENV NODE_ENV=production \
    VITE_API_URL=${VITE_API_URL} \
    VITE_APP_VERSION=${VITE_APP_VERSION}

RUN if [ -f package-lock.json ]; then \
      npm run build; \
    elif [ -f yarn.lock ]; then \
      corepack enable yarn && yarn build; \
    elif [ -f pnpm-lock.yaml ]; then \
      corepack enable pnpm && pnpm build; \
    fi

# =============================================================================
# Stage: python-builder — install backend workspace into .venv
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-trixie AS python-builder

ARG BACKEND_DIR

COPY --from=uv /uv /uvx /bin/

WORKDIR /workspace

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./
COPY shared/ shared/
COPY backend/pyproject.toml backend/README.md ./backend/
COPY agent/pyproject.toml agent/README.md ./agent/

WORKDIR /workspace/${BACKEND_DIR}

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

COPY shared/ /workspace/shared/
COPY ${BACKEND_DIR}/ /workspace/${BACKEND_DIR}/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# =============================================================================
# Stage: runner — Python API + bundled static files
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-trixie AS runner

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS
ARG IMAGE_TITLE

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
      org.opencontainers.image.description="Nexo Co-Review (nexo-coreview) — Python API with bundled Vite React SPA" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.authors="${IMAGE_AUTHORS}"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    APP_VERSION=${VERSION} \
    STATIC_DIR=/app/static \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 999 app \
 && useradd --system --gid 999 --uid 999 --create-home app

COPY --from=python-builder --chown=app:app /app/.venv /app/.venv
COPY --from=python-builder --chown=app:app /workspace/backend /app
COPY --from=frontend-builder --chown=app:app /app/dist /app/static

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
