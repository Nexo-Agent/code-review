.PHONY: dev dev-watch dev-down up down prod-up migrate migrate-down openapi lint test test-unit build-agent render-opencode-config ensure-opencode-config

ifneq (,$(wildcard .env))
include .env
export
endif

COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yaml

# Bind-mount target; avoid Docker creating a directory on first boot.
ensure-opencode-config:
	@test -f opencode.generated.json || touch opencode.generated.json

# --- Stack lifecycle (Docker Compose only) ---

dev: ensure-opencode-config
	$(COMPOSE) up --build

dev-watch: ensure-opencode-config
	$(COMPOSE) watch

dev-down: down

up: prod-up

prod-up: ensure-opencode-config
	$(COMPOSE_PROD) --profile prod up --build -d --wait

down:
	$(COMPOSE) down

# --- Init / maintenance (runs via Compose services) ---

migrate:
	$(COMPOSE) run --rm migrate

migrate-down:
	$(COMPOSE) --profile tools run --rm migrate-down

render-opencode-config: migrate ensure-opencode-config
	$(COMPOSE) run --rm render-opencode

build-agent:
	$(COMPOSE) build agent-image

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
