---
description: Dockerfile guide for Next.js App Router apps — standalone output, multi-stage Node build, minimal production runner.
---

# Next.js Dockerfile

Use this reference when the project is a **Next.js application** that needs full
framework features at runtime (SSR, API routes, Server Actions, etc.).

Template: [assets/nextjs.Dockerfile](../assets/nextjs.Dockerfile)

## When to use

- `next` in `package.json` dependencies
- Production deployment as a Node.js server (not static export)

## Required project config

The Dockerfile expects **`output: "standalone"`** in `next.config.ts` (or
`.js`/`.mjs`):

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

Without this, `.next/standalone` is not generated and the runner stage will fail.
Tell the user to add this before building.

## Architecture

Based on the official
[with-docker example](https://github.com/vercel/next.js/tree/canary/examples/with-docker):

```
dependencies (node)  →  npm ci / yarn / pnpm install (lockfile only)
builder (node)       →  copy source + node_modules, next build
runner (node slim)   →  copy .next/standalone + static + public
```

The standalone output traces only the files needed at runtime, keeping the image
small relative to copying all of `node_modules`.

## Runner stage contents

```dockerfile
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
```

Run as the `node` user (provided by official Node images).

## Build-time version embedding

```dockerfile
ARG NEXT_PUBLIC_APP_VERSION
ENV NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION
```

Set from the shared `VERSION` build arg in CI.

## Environment at runtime

```dockerfile
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
```

Pass secrets and environment-specific values via `docker run -e` or orchestrator
config — do not bake secrets into the image.

## Customization points

| Placeholder | Default | Change when |
| --- | --- | --- |
| `NODE_VERSION` | `22-slim` | Project requires specific Node LTS |
| `PORT` | `3000` | Platform expects a different port |
| Monorepo | root context | Adjust `WORKDIR` and copy paths |

## Static export alternative

If the user only needs static HTML export (`output: "export"`), they do **not**
need this Next.js Node template — use the
[vite-react](vite-react.md) nginx pattern instead (build with `next build` but
serve `out/` via nginx). Only suggest this when the user confirms they do not
need SSR or API routes.

## Verification

```bash
docker build -t my-next-app .
docker run --rm -p 3000:3000 my-next-app
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Confirm `output: "standalone"` is set and `server.js` starts in the runner.
