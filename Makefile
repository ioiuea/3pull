FRONTEND_DIR := apps/frontend
BACKEND_DIR := apps/backend

ifneq ("$(wildcard $(BACKEND_DIR)/.env)","")
include $(BACKEND_DIR)/.env
endif

GUNICORN_WORKERS ?= 2
GUNICORN_THREADS ?= 1
GUNICORN_TIMEOUT ?= 60
GUNICORN_KEEPALIVE ?= 5

# `make alembic-revision "<任意のメッセージ>"` 実行時のみ、
# メッセージ文字列が未定義ターゲットとして解釈されても無視して続行する。
ALEMBIC_MESSAGE := $(strip $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS)))
ifneq (,$(filter alembic-revision,$(MAKECMDGOALS)))
.DEFAULT:
	@:
endif

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
.PHONY: backend-install alembic-revision alembic-upgrade

backend-install:
	cd $(BACKEND_DIR) && uv sync --frozen

backend-format:
	uv --directory $(BACKEND_DIR) run ruff format --check app

backend-format-fix:
	uv --directory $(BACKEND_DIR) run ruff format app

alembic-revision:
	@test -n "$(ALEMBIC_MESSAGE)" || (echo 'Usage: make alembic-revision "your migration message"' && exit 1)
	cd $(BACKEND_DIR) && uv run alembic revision --autogenerate -m "$(ALEMBIC_MESSAGE)"

alembic-upgrade:
	cd $(BACKEND_DIR) && uv run alembic upgrade head

# ------------------------------
# Combined runtime targets
# ------------------------------
.PHONY: install env up up-api up-web dev dev-api dev-web

install: frontend-install backend-install

env:
	@if [ -f "$(FRONTEND_DIR)/.env.example" ] && [ ! -f "$(FRONTEND_DIR)/.env" ]; then \
		cp "$(FRONTEND_DIR)/.env.example" "$(FRONTEND_DIR)/.env"; \
		echo "Created $(FRONTEND_DIR)/.env from .env.example"; \
	fi
	@if [ -f "$(BACKEND_DIR)/.env.example" ] && [ ! -f "$(BACKEND_DIR)/.env" ]; then \
		cp "$(BACKEND_DIR)/.env.example" "$(BACKEND_DIR)/.env"; \
		echo "Created $(BACKEND_DIR)/.env from .env.example"; \
	fi

# `up-api` は本番相当（Gunicorn）で API を起動できるか確認する用途。
# macOS では fork 後の Objective-C 初期化安全性チェックで worker が SIGABRT し得るため、
# ローカル検証時はこの環境変数で回避する。
up-api: env backend-install
	cd $(BACKEND_DIR) && OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run gunicorn app.main:app \
		-k uvicorn.workers.UvicornWorker \
		--bind 0.0.0.0:8000 \
		--workers $(GUNICORN_WORKERS) \
		--threads $(GUNICORN_THREADS) \
		--timeout $(GUNICORN_TIMEOUT) \
		--keep-alive $(GUNICORN_KEEPALIVE)

# `up-web` は本番相当（build + preview）で SSR false のビルド/起動確認を行う用途。
up-web: env frontend-install
	cd $(FRONTEND_DIR) && pnpm run build && pnpm run preview

# `up` は `up-api` と `up-web` を別サブシェルで同時起動する用途。
up:
	@trap 'kill 0' INT TERM EXIT; \
	( $(MAKE) up-api ) & \
	( $(MAKE) up-web ) & \
	wait

# `dev-api` はホットリロード有効（uvicorn --reload）で API 開発を行う用途。
dev-api: env backend-install
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log

# `dev-web` はホットリロード有効（pnpm run dev）で Web 開発を行う用途。
dev-web: env frontend-install
	cd $(FRONTEND_DIR) && pnpm run dev

# `dev` は `dev-api` と `dev-web` を別サブシェルで同時起動する用途。
dev:
	@trap 'kill 0' INT TERM EXIT; \
	( $(MAKE) dev-api ) & \
	( $(MAKE) dev-web ) & \
	wait
