export PATH := $(HOME)/bin:$(PATH)
export DOCKER_HOST ?= unix:///run/user/$(shell id -u)/docker.sock
COMPOSE=docker compose -f infra/docker-compose.yml --env-file .env

.PHONY: dev down test lint seed migrate
dev: ; test -f .env || cp .env.example .env; $(COMPOSE) up --build
down: ; $(COMPOSE) down
migrate: ; $(COMPOSE) run --rm backend alembic upgrade head
seed: ; $(COMPOSE) run --rm backend python -m app.seed
test: ; cd backend && python -m pytest
lint: ; cd backend && ruff check . && black --check . && mypy app; cd frontend && npm run lint
