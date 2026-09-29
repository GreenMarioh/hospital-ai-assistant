# Rootless Docker installs put the CLI in ~/bin and the socket under /run/user/<uid>.
ROOTLESS_SOCK := /run/user/$(shell id -u)/docker.sock
ifneq ($(wildcard $(ROOTLESS_SOCK)),)
export DOCKER_HOST ?= unix://$(ROOTLESS_SOCK)
export PATH := $(HOME)/bin:$(PATH)
endif
COMPOSE=docker compose -f infra/docker-compose.yml --env-file .env
COMPOSE_E2E=docker compose -f infra/docker-compose.yml -f infra/docker-compose.e2e.yml --env-file .env

.PHONY: init-env dev up down test lint seed migrate backend-venv load-test
init-env: ; python3 infra/scripts/init_env.py
dev: init-env ; $(COMPOSE) up --build
up: init-env ; $(COMPOSE) up -d --build --wait
down: ; $(COMPOSE) down
migrate: ; $(COMPOSE) run --rm backend alembic upgrade head
seed: ; $(COMPOSE) run --rm backend python -m app.seed
backend-venv: ; python3 -m venv backend/.venv && backend/.venv/bin/pip install -e 'backend[dev]'
test: ; cd backend && .venv/bin/python -m pytest --cov=app && cd ../frontend && npm test
load-test: ; k6 run -e BASE_URL=http://localhost:8000 loadtest/k6.js
lint: ; cd backend && .venv/bin/ruff check . && .venv/bin/black --check . && .venv/bin/mypy app && cd ../frontend && npm run lint && npm run typecheck

.PHONY: e2e-up e2e
e2e-up: init-env ; $(COMPOSE_E2E) up -d --build --wait && $(COMPOSE_E2E) exec -T backend python -m app.seed
e2e: e2e-up ; cd frontend && npx playwright test

.PHONY: api-docs
api-docs: ; python3 infra/scripts/gen_api_docs.py && cd frontend && npm run gen:api
