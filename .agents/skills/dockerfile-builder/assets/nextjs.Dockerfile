# syntax=docker/dockerfile:1

# --- Build metadata ---
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS="Your Name <you@example.com>"
ARG IMAGE_TITLE="nextjs-app"

# --- Tool versions ---
ARG NODE_VERSION=22-slim

# =============================================================================
# Stage: dependencies — install node_modules from lockfile
# =============================================================================
FROM node:${NODE_VERSION} AS dependencies

WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* .npmrc* ./

RUN --mount=type=cache,target=/root/.npm \
    --mount=type=cache,target=/usr/local/share/.cache/yarn \
    --mount=type=cache,target=/root/.local/share/pnpm/store \
    if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
    elif [ -f yarn.lock ]; then \
      corepack enable yarn && yarn install --frozen-lockfile --production=false; \
    elif [ -f pnpm-lock.yaml ]; then \
      corepack enable pnpm && pnpm install --frozen-lockfile; \
    else \
      echo "No lockfile found." && exit 1; \
    fi

# =============================================================================
# Stage: builder — next build (requires output: "standalone")
# =============================================================================
FROM node:${NODE_VERSION} AS builder

ARG VERSION
ARG NEXT_PUBLIC_APP_VERSION=${VERSION}

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

ENV NODE_ENV=production \
    NEXT_PUBLIC_APP_VERSION=${NEXT_PUBLIC_APP_VERSION}

RUN if [ -f package-lock.json ]; then \
      npm run build; \
    elif [ -f yarn.lock ]; then \
      corepack enable yarn && yarn build; \
    elif [ -f pnpm-lock.yaml ]; then \
      corepack enable pnpm && pnpm build; \
    fi

# =============================================================================
# Stage: runner — standalone Node server
# =============================================================================
FROM node:${NODE_VERSION} AS runner

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS
ARG IMAGE_TITLE

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
      org.opencontainers.image.description="Next.js application (standalone)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.authors="${IMAGE_AUTHORS}"

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0" \
    APP_VERSION=${VERSION}

RUN mkdir .next && chown node:node .next

COPY --from=builder /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
