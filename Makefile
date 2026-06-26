.PHONY: help dev prod prod-down migrate migrate-down openapi lint test test-unit build-agent render-opencode-config pre-commit-install pre-commit

ifneq (,$(wildcard .env))
include .env
export
endif

COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yaml
AGENT_IMAGE ?= $(or $(COGITO_REVIEW_AGENT_IMAGE),cogito-review-agent:dev)

help:
	@printf "%s\n" \
		"Available targets:" \
		"  help                  Show this help message" \
		"  dev                   Start the development stack with Compose Watch" \
		"  prod                  Start the production-like stack from docker-compose.yaml" \
		"  prod-down             Stop the production-like stack" \
		"  migrate               Run database migrations via Compose" \
		"  migrate-down          Roll back the latest database migration via Compose" \
		"  build-agent           Build the local agent image" \
		"  render-opencode-config Render backend OpenCode config on the host" \
		"  openapi               Export OpenAPI and regenerate frontend types" \
		"  lint                  Run Ruff, ESLint, and TypeScript checks" \
		"  test-unit             Run unit test suites" \
		"  test                  Run unit and integration tests" \
		"  pre-commit-install    Install local pre-commit hooks" \
		"  pre-commit            Run pre-commit on all files"

# --- Stack lifecycle (Docker Compose only) ---

dev: build-agent
	$(COMPOSE) watch

prod:
	$(COMPOSE_PROD) pull
	$(COMPOSE_PROD) up -d --wait

prod-down:
	$(COMPOSE_PROD) down

# --- Init / maintenance (runs via Compose services) ---

migrate:
	$(COMPOSE) run --build --rm migrate

migrate-down:
	$(COMPOSE) --profile tools run --build --rm migrate-down

render-opencode-config: migrate
	cd backend && uv run cogito-review config render-opencode

build-agent:
	docker build -f agent/Dockerfile \
		--build-arg VERSION=$(or $(VERSION),dev) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg VCS_REF=$(VCS_REF) \
		-t $(AGENT_IMAGE) \
		.

# --- Developer tooling (host uv/yarn; not part of runtime stack) ---

openapi:
	cd backend && uv run python -c "import json; from app.main import create_app; app = create_app(); open('../openapi.json', 'w').write(json.dumps(app.openapi(), indent=2))"
	cd frontend && yarn openapi:generate

lint:
	cd shared && uv run ruff check .
	cd backend && uv run ruff check .
	cd agent && uv run ruff check .
	cd frontend && yarn lint && yarn typecheck

test:
	cd backend && uv run pytest
	cd backend && uv run pytest -m integration

test-unit:
	cd shared && uv run pytest
	cd backend && uv run pytest -m "not integration"
	cd agent && uv run pytest

pre-commit-install:
	uv sync --locked --group dev
	cd shared && uv sync --locked --all-groups
	cd backend && uv sync --locked --all-groups
	cd agent && uv sync --locked --all-groups
	cd frontend && corepack enable yarn && yarn install --frozen-lockfile
	uv run pre-commit install

pre-commit:
	uv run pre-commit run --all-files
