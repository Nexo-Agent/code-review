# syntax=docker/dockerfile:1

# --- Build metadata ---
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS="Your Name <you@example.com>"
ARG IMAGE_TITLE="python-app"

# --- Tool versions ---
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.11.21

# =============================================================================
# Stage: builder — install dependencies and project into .venv
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-trixie AS builder

ARG UV_VERSION
COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

# Install transitive dependencies (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# Copy source and install the project (non-editable)
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# =============================================================================
# Stage: runner — minimal runtime with .venv only
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-trixie AS runner

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS
ARG IMAGE_TITLE

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
      org.opencontainers.image.description="Python application (uv)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.authors="${IMAGE_AUTHORS}"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    APP_VERSION=${VERSION} \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 999 app \
 && useradd --system --gid 999 --uid 999 --create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

USER app

EXPOSE 8000

# Replace with your entry point (console script or module)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
