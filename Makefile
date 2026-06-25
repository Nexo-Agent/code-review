.PHONY: dev dev-watch dev-down up down prod-up migrate migrate-down openapi lint test test-unit build-agent render-opencode-config

ifneq (,$(wildcard .env))
include .env
export
endif

COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yaml
AGENT_IMAGE ?= $(or $(NEXO_COREVIEW_AGENT_IMAGE),code-review-agent:dev)

# --- Stack lifecycle (Docker Compose only) ---

dev: build-agent
	$(COMPOSE) up --build

dev-watch: build-agent
	$(COMPOSE) watch

dev-down: down

up: prod-up

prod-up:
	$(COMPOSE_PROD) pull
	$(COMPOSE_PROD) up -d --wait

down:
	$(COMPOSE) down

# --- Init / maintenance (runs via Compose services) ---

migrate:
	$(COMPOSE) run --rm migrate

migrate-down:
	$(COMPOSE) --profile tools run --rm migrate-down

render-opencode-config: migrate
	cd backend && uv run code-review config render-opencode

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
	cd shared && uv run ruff check . && uv run ruff format --check .
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd agent && uv run ruff check . && uv run ruff format --check .
	cd frontend && yarn lint && yarn typecheck

test:
	cd backend && uv run pytest
	cd backend && uv run pytest -m integration

test-unit:
	cd shared && uv run pytest
	cd backend && uv run pytest -m "not integration"
	cd agent && uv run pytest
