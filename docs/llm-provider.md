# LLM Provider

## Purpose

LLM providers represent reusable model endpoint profiles that the system can use during code review runs.

The current design is intentionally simple:

- the platform stores one or more provider configurations in PostgreSQL
- a repository integration may optionally choose one specific provider
- otherwise the organization default provider is used
- the chosen provider is materialized into an OpenCode configuration at runtime

## Current abstraction

The system does not implement separate vendor SDK adapters for every model vendor.

Instead, each provider is stored as an OpenAI-compatible endpoint profile with:

- `provider_id`
- `base_url`
- `api_token`
- `model`
- optional `opencode_model`

This design allows the platform to support many vendors through the same runtime shape as long as they expose an OpenAI-compatible API surface that OpenCode can consume.

## Main data model

Table: `llm_providers`

Important fields:

- name
- provider_id
- base_url
- api_token
- model
- opencode_model
- is_default
- enabled
- organization_id

## Resolution rules

LLM provider resolution happens in `backend/app/services/provider_resolution.py`.

Current logic:

1. if a repository integration has `llm_provider_id`, use it if it belongs to the same organization and is enabled
2. otherwise fall back to the organization default provider
3. if no valid provider exists, review execution cannot start

## Where LLM providers are used

### Settings UI and API

Management endpoints:

- `GET /api/v1/settings/llm-providers`
- `POST /api/v1/settings/llm-providers`
- `PUT /api/v1/settings/llm-providers/{id}`
- `DELETE /api/v1/settings/llm-providers/{id}`

### Review job preparation

When a review job is prepared, the backend injects the resolved provider into the agent environment:

- `COGITO_REVIEW_LLM_PROVIDER_ID`
- `COGITO_REVIEW_LLM_BASE_URL`
- `COGITO_REVIEW_LLM_API_TOKEN`
- `COGITO_REVIEW_LLM_MODEL`
- `COGITO_REVIEW_OPENCODE_MODEL`

### OpenCode config generation

The backend can generate an OpenCode config containing all enabled LLM providers.

Related files:

- `backend/app/providers/opencode_config.py`
- `backend/app/services/provider_resolution.py`

### Agent review execution

The agent uses the resolved provider values when launching OpenCode for the review run.

## `provider_id` versus `opencode_model`

Two related but different concepts exist:

### `provider_id`

Logical provider name used in generated OpenCode config, for example the namespace before the model name.

### `opencode_model`

Optional explicit OpenCode model reference.

If `opencode_model` is empty, the resolved OpenCode model becomes:

`<provider_id>/<model>`

This allows normal cases to stay simple while still supporting custom OpenCode naming when needed.

## Enabled and default behavior

Current behavior:

- only enabled providers are considered for generated OpenCode config
- one provider may be marked as default per organization
- repository-level override is optional

## Security model

LLM API tokens are persisted in PostgreSQL and surfaced back to the UI only as “configured” booleans, not raw secret values.

The backend treats these tokens as operational secrets and injects them into the agent only for the relevant review run.

## Adding another LLM provider

For the current architecture, adding support for a new provider usually means configuration rather than new code.

If the endpoint is OpenAI-compatible:

1. add a new provider row through settings
2. choose its `provider_id`, `base_url`, and `model`
3. optionally set `opencode_model`

New code is only needed when the provider requires behavior that cannot fit the current OpenAI-compatible profile model.

## Current architectural trade-off

Benefits of the current design:

- simple operational model
- low backend complexity
- works well with OpenCode
- easy per-repository override

Trade-offs:

- advanced vendor-specific features are not modeled directly
- compatibility depends on OpenCode and the endpoint behaving like the expected OpenAI-style API
