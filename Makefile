FRONTEND_DIR := apps/frontend
BACKEND_DIR := apps/backend

ifneq ("$(wildcard $(BACKEND_DIR)/.env)","")
include $(BACKEND_DIR)/.env
endif

GUNICORN_WORKERS ?= 2
GUNICORN_THREADS ?= 1
GUNICORN_TIMEOUT ?= 60
GUNICORN_KEEPALIVE ?= 5

# ------------------------------
# Frontend targets
# ------------------------------
.PHONY: frontend-install frontend-format frontend-format-fix frontend-lint frontend-lint-fix frontend-typecheck frontend-test frontend-ci

frontend-install:
	pnpm --dir $(FRONTEND_DIR) install --frozen-lockfile

frontend-format:
	pnpm --dir $(FRONTEND_DIR) run format

frontend-format-fix:
	pnpm --dir $(FRONTEND_DIR) run format:fix

frontend-lint:
	pnpm --dir $(FRONTEND_DIR) run lint

frontend-lint-fix:
	pnpm --dir $(FRONTEND_DIR) run lint:fix

frontend-typecheck:
	pnpm --dir $(FRONTEND_DIR) run typecheck:ci

frontend-test:
	pnpm --dir $(FRONTEND_DIR) run test:run

frontend-ci: frontend-format frontend-lint frontend-typecheck frontend-test

# ------------------------------
# Backend targets
# ------------------------------
.PHONY: backend-install env-init up up-dev

backend-install:
	cd $(BACKEND_DIR) && uv sync --frozen

# ------------------------------
# Combined runtime targets
# ------------------------------
env-init:
	@if [ -f "$(FRONTEND_DIR)/.env.example" ] && [ ! -f "$(FRONTEND_DIR)/.env" ]; then \
		cp "$(FRONTEND_DIR)/.env.example" "$(FRONTEND_DIR)/.env"; \
		echo "Created $(FRONTEND_DIR)/.env from .env.example"; \
	fi
	@if [ -f "$(BACKEND_DIR)/.env.example" ] && [ ! -f "$(BACKEND_DIR)/.env" ]; then \
		cp "$(BACKEND_DIR)/.env.example" "$(BACKEND_DIR)/.env"; \
		echo "Created $(BACKEND_DIR)/.env from .env.example"; \
	fi

up: env-init frontend-install backend-install
	@trap 'kill 0' INT TERM EXIT; \
	( cd $(BACKEND_DIR) && uv run gunicorn app.main:app \
		-k uvicorn.workers.UvicornWorker \
		--bind 0.0.0.0:8000 \
		--workers $(GUNICORN_WORKERS) \
		--threads $(GUNICORN_THREADS) \
		--timeout $(GUNICORN_TIMEOUT) \
		--keep-alive $(GUNICORN_KEEPALIVE) ) & \
	( cd $(FRONTEND_DIR) && pnpm run build && pnpm run preview ) & \
	wait

up-dev: env-init frontend-install backend-install
	@trap 'kill 0' INT TERM EXIT; \
	( cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log ) & \
	( cd $(FRONTEND_DIR) && pnpm run dev ) & \
	wait
