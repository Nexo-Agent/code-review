# Frontend

## Role in the system

The frontend is the browser UI for operating the platform.

It covers:

- install and login
- dashboard
- teams and members
- repositories
- reviews and findings
- LLM provider settings
- identity provider settings
- RBAC permission settings

The frontend is built as a React single-page application and served by the backend in production.

## Technology stack

Current stack from `frontend/package.json`:

- React 19
- Vite
- TanStack Router
- TanStack Query
- TanStack Table
- Tailwind CSS v4
- shadcn/ui and Radix primitives
- `react-markdown` for finding bodies
- `sonner` for toast notifications

## Application bootstrap

Entrypoint: `frontend/src/main.tsx`

Bootstrap responsibilities:

- create the shared `QueryClient`
- create the TanStack Router instance
- wrap the app in `QueryClientProvider`
- enable devtools in development

## Routing model

The app uses file-based routing with TanStack Router.

Key route files:

- `routes/__root.tsx`
- `routes/index.tsx`
- `routes/install.tsx`
- `routes/login.tsx`
- `routes/teams/...`
- `routes/repositories/...`
- `routes/reviews/...`
- `routes/llm-providers/...`
- `routes/settings/identity-provider.tsx`
- `routes/settings/permissions.tsx`

Generated route manifest:

- `frontend/src/routeTree.gen.ts`

Do not edit the generated route tree manually.

## Root route behavior

`routes/__root.tsx` performs global routing checks:

1. query install status
2. redirect to `/install` if first-run setup is required
3. allow `/login` without current session
4. fetch `/auth/me` for authenticated routes
5. redirect unauthenticated users to `/login`

This gives the frontend a single place for install and auth gating.

## State management

The frontend uses server-state-first patterns.

### Remote state

TanStack Query hooks are the main state layer for server data.

Examples:

- `useReviews`
- `useTeams`
- `useSettings`
- `useIdentityProvider`
- `useRbac`

### Route state

List pages store filters and pagination in route search params.

Examples:

- reviews list
- repositories list
- teams list

This makes filtering shareable through the URL and keeps page state predictable.

### Local UI state

Component-local `useState` is used for:

- dialog visibility
- form state
- filters before debounced commit
- debug panel toggles

## Page organization

### Dashboard

Shows:

- system health
- counts for configured repositories
- counts for reviews
- counts for LLM providers

### Teams

Supports:

- team list
- team creation
- team detail
- member list and member management
- repository list for a team

### Repositories

Supports organization-wide browsing of repository integrations with filters for:

- search text
- team
- enabled status
- Git provider

### Reviews

Supports:

- paginated review list
- filtering by status and repository
- review detail with metadata, findings, and historical runs
- retry action subject to RBAC permissions

### Settings

Today settings are split across dedicated routes rather than a single landing page:

- repositories
- LLM providers
- identity provider
- permissions

`/settings` currently redirects to `/repositories`.

## UI composition

The UI structure is intentionally split into:

- `components/layout`: shell and page framing
- `components/patterns`: reusable app-level patterns
- `components/ui`: low-level design primitives
- `components/reviews`, `components/teams`, `components/settings`: feature-specific components

This keeps feature pages readable without introducing an overly abstract design system layer.

## API integration

The frontend uses a central API client and typed request helpers.

Important folders:

- `src/api/`
- `src/hooks/`

Generated backend contract:

- `src/api/generated/schema.ts`

## Permission-aware UI

The frontend reads effective permissions from `/auth/me`.

Typical behavior:

- hide create or edit actions when permission is missing
- redirect away from restricted settings pages
- still rely on backend `403` as the real enforcement layer

This keeps the UI aligned with RBAC without moving authorization logic into the client.

## Review presentation model

Review detail pages currently expose three main perspectives:

- metadata and delivery stats
- findings list with severity filtering and file grouping
- historical runs for the same PR

Finding bodies are rendered as Markdown.

## Current design characteristics

- single SPA, no server-side rendering
- URL-driven filters on list pages
- server state centered on TanStack Query
- strong coupling to backend OpenAPI contract
- permission-aware navigation and actions
