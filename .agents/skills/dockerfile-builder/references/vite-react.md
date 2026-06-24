---
description: Dockerfile guide for Vite + React SPAs — Node build stage and nginx runner serving static assets.
---

# Vite + React Dockerfile

Use this reference when the project is a **Vite-powered React SPA** that builds
to static files (`dist/`).

Template: [assets/vite-react.Dockerfile](../assets/vite-react.Dockerfile)  
Nginx config: [assets/nginx-spa.conf](../assets/nginx-spa.conf)

## When to use

- `vite.config.ts` / `vite.config.js` with React
- `npm run build` (or `pnpm` / `yarn`) produces a `dist/` directory
- No server-side rendering at runtime — static hosting is sufficient

## Architecture

```
dependencies (node)  →  install node_modules from lockfile
builder (node)       →  npm run build → dist/
runner (nginx:alpine)→  copy dist/ + nginx config, serve on port 80
```

The final image contains **only** nginx and static files — no Node.js runtime.

## Nginx SPA routing

Single-page apps need a fallback to `index.html` for client-side routes. Use the
bundled [assets/nginx-spa.conf](../assets/nginx-spa.conf):

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

Copy it in the Dockerfile:

```dockerfile
COPY assets/nginx-spa.conf /etc/nginx/conf.d/default.conf
```

If the project already has a custom `nginx.conf`, prefer the project's file.

## Build-time environment variables

Vite exposes only variables prefixed with `VITE_`. Pass them as build args:

```dockerfile
ARG VITE_API_URL
ARG VITE_APP_VERSION
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_APP_VERSION=$VITE_APP_VERSION
```

Set `VITE_APP_VERSION` from the shared `VERSION` build arg so the built bundle
embeds release info.

## Package manager detection

The template auto-detects the lockfile (`package-lock.json`, `yarn.lock`,
`pnpm-lock.yaml`). Match the lockfile present in the project — do not mix
managers.

## Customization points

| Placeholder | Default | Change when |
| --- | --- | --- |
| `NODE_VERSION` | `22-alpine` | Project requires a specific Node LTS |
| `NGINX_VERSION` | `alpine` | Pin nginx for compliance |
| Build output dir | `dist` | Vite `build.outDir` is customized |
| `EXPOSE` | `80` | Behind reverse proxy on a different port |

## API proxy (optional)

If the SPA calls a backend API and you want nginx to proxy (same-origin), add a
`location /api/` block in nginx config. For separate backend deployments, configure
`VITE_API_URL` instead — do not proxy unless the user asks.

## Verification

```bash
docker build \
  --build-arg VERSION=1.0.0 \
  --build-arg VITE_APP_VERSION=1.0.0 \
  -t my-spa .
docker run --rm -p 8080:80 my-spa
```

Open `http://localhost:8080`, confirm assets load, and client-side routes work
on refresh.
