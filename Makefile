.PHONY: dev-db dev-api dev-web dev dev-watch dev-down dev-migrate dev-worker migrate migrate-down openapi prod-up lint test render-opencode-config

ifneq (,$(wildcard .env))
include .env
export
endif

DATABASE_URL ?= postgresql://app:app@localhost:5432/app?sslmode=disable
COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yaml
MIGRATIONS_DIR := backend/migrations

dev-db:
	docker compose up -d db redis

# Native local dev (no Docker for app processes)
dev-api:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $${APP_PORT:-8000}

dev-web:
	cd frontend && yarn dev

dev-worker:
	cd backend && uv run code-review job worker

dev-opencode-serve: render-opencode-config
	docker compose up -d opencode-serve

render-opencode-config:
	cd backend && uv run code-review config render-opencode -o ../opencode.generated.json

opencode.generated.json:
	@test -f opencode.generated.json || echo '{"$$schema":"https://opencode.ai/config.json"}' > opencode.generated.json

# Docker dev: merges docker-compose.yaml + docker-compose.override.yaml
dev: opencode.generated.json
	$(COMPOSE) up --build

dev-watch: opencode.generated.json
	$(COMPOSE) watch

dev-down:
	$(COMPOSE) down

dev-migrate:
	$(COMPOSE) --profile tools run --rm migrate

migrate:
	docker run --rm \
		-e DATABASE_URL="$(DATABASE_URL)" \
		-v "$(CURDIR)/$(MIGRATIONS_DIR):/db/migrations" \
		--network host \
		ghcr.io/amacneil/dbmate:2 \
		-d /db/migrations --wait up

migrate-down:
	docker run --rm \
		-e DATABASE_URL="$(DATABASE_URL)" \
		-v "$(CURDIR)/$(MIGRATIONS_DIR):/db/migrations" \
		--network host \
		ghcr.io/amacneil/dbmate:2 \
		-d /db/migrations down

openapi:
	cd backend && uv run python -c "import json; from app.main import create_app; app = create_app(); open('../openapi.json', 'w').write(json.dumps(app.openapi(), indent=2))"
	cd frontend && yarn openapi:generate

prod-up: opencode.generated.json
	$(COMPOSE_PROD) --profile prod up --build -d

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && yarn lint && yarn typecheck

test:
	cd backend && uv run pytest
	cd backend && uv run pytest -m integration

test-unit:
	cd backend && uv run pytest
