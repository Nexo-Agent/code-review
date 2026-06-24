# syntax=docker/dockerfile:1

# --- Build metadata ---
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS="Your Name <you@example.com>"
ARG IMAGE_TITLE="vite-react-app"

# --- Tool versions ---
ARG NODE_VERSION=22-alpine
ARG NGINX_VERSION=alpine

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
      corepack enable yarn && yarn install --frozen-lockfile; \
    elif [ -f pnpm-lock.yaml ]; then \
      corepack enable pnpm && pnpm install --frozen-lockfile; \
    else \
      echo "No lockfile found." && exit 1; \
    fi

# =============================================================================
# Stage: builder — build static assets
# =============================================================================
FROM node:${NODE_VERSION} AS builder

ARG VERSION
ARG VITE_API_URL
ARG VITE_APP_VERSION=${VERSION}

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

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
# Stage: runner — nginx serves dist/
# =============================================================================
FROM nginx:${NGINX_VERSION} AS runner

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG IMAGE_AUTHORS
ARG IMAGE_TITLE

LABEL org.opencontainers.image.title="${IMAGE_TITLE}" \
      org.opencontainers.image.description="Vite React SPA (nginx)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.authors="${IMAGE_AUTHORS}"

# Replace with project nginx config if one exists
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
