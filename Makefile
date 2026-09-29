export PATH := $(HOME)/bin:$(PATH)
export DOCKER_HOST ?= unix:///run/user/$(shell id -u)/docker.sock
COMPOSE=docker compose -f infra/docker-compose.yml --env-file .env
COMPOSE_E2E=docker compose -f infra/docker-compose.yml -f infra/docker-compose.e2e.yml --env-file .env

.PHONY: dev down test lint seed migrate
dev: ; test -f .env || cp .env.example .env; $(COMPOSE) up --build
down: ; $(COMPOSE) down
migrate: ; $(COMPOSE) run --rm backend alembic upgrade head
seed: ; $(COMPOSE) run --rm backend python -m app.seed
test: ; cd backend && python -m pytest
lint: ; cd backend && ruff check . && black --check . && mypy app; cd frontend && npm run lint

.PHONY: e2e-up e2e
e2e-up: ; test -f .env || cp .env.example .env; $(COMPOSE_E2E) up -d --build --wait && $(COMPOSE_E2E) exec -T backend python -m app.seed
e2e: e2e-up ; cd frontend && npx playwright test
