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
.PHONY: backend-install backend-format backend-format-fix backend-lint backend-lint-fix backend-typecheck backend-test backend-ci alembic-revision alembic-upgrade schedulers-sessions schedulers-sessions-dry-run schedulers-audit schedulers-audit-dry-run schedulers-jobs schedulers-jobs-dry-run

backend-install:
	cd $(BACKEND_DIR) && uv sync --frozen

backend-format:
	uv --directory $(BACKEND_DIR) run ruff format --check app

backend-format-fix:
	uv --directory $(BACKEND_DIR) run ruff format app

backend-lint:
	uv --directory $(BACKEND_DIR) run ruff check app

backend-lint-fix:
	uv --directory $(BACKEND_DIR) run ruff check --fix app

backend-typecheck:
	uv --directory $(BACKEND_DIR) run pyright app

backend-test:
	uv --directory $(BACKEND_DIR) run pytest

backend-ci: backend-format backend-lint backend-typecheck backend-test

alembic-revision:
	@test -n "$(ALEMBIC_MESSAGE)" || (echo 'Usage: make alembic-revision "your migration message"' && exit 1)
	cd $(BACKEND_DIR) && uv run alembic revision --autogenerate -m "$(ALEMBIC_MESSAGE)"

alembic-upgrade:
	cd $(BACKEND_DIR) && uv run alembic upgrade head

schedulers-sessions:
	uv --directory $(BACKEND_DIR) run python -m app.schedulers.batch_jobs sessions-cleanup

schedulers-sessions-dry-run:
	uv --directory $(BACKEND_DIR) run python -m app.schedulers.batch_jobs sessions-cleanup --dry-run

schedulers-audit:
	uv --directory $(BACKEND_DIR) run python -m app.schedulers.batch_jobs audit-cleanup

schedulers-audit-dry-run:
	uv --directory $(BACKEND_DIR) run python -m app.schedulers.batch_jobs audit-cleanup --dry-run

schedulers-jobs:
	uv --directory $(BACKEND_DIR) run python -m app.schedulers.batch_jobs jobs-cleanup

schedulers-jobs-dry-run:
	uv --directory $(BACKEND_DIR) run python -m app.schedulers.batch_jobs jobs-cleanup --dry-run

# ------------------------------
# Docker targets
# ------------------------------
.PHONY: docker-build docker-build-api docker-build-worker docker-build-schedulers docker-build-web docker-push docker-push-api docker-push-worker docker-push-schedulers docker-push-web docker-run-api docker-run-worker-auth-audit-export docker-run-worker-sample-wait-blob docker-run-schedulers-sessions docker-run-schedulers-audit docker-run-schedulers-jobs-dry-run docker-run-web

DOCKER_API_IMAGE ?= 3pull-api:local
DOCKER_WORKER_IMAGE ?= 3pull-worker:local
DOCKER_SCHEDULERS_IMAGE ?= 3pull-schedulers:local
DOCKER_WEB_IMAGE ?= 3pull-web:local
DOCKER_BUILD_PLATFORM ?= linux/amd64

docker-build-api:
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --load -f docker/api.Dockerfile -t $(DOCKER_API_IMAGE) .

docker-build-worker:
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --load -f docker/worker.Dockerfile -t $(DOCKER_WORKER_IMAGE) .

docker-build-schedulers:
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --load -f docker/schedulers.Dockerfile -t $(DOCKER_SCHEDULERS_IMAGE) .

docker-build-web:
	@test -n "$(VITE_BACKEND_BASE_URL)" || (echo 'VITE_BACKEND_BASE_URL must be set for docker-build-web' && exit 1)
	@test -n "$(VITE_PRODUCT_NAME)" || (echo 'VITE_PRODUCT_NAME must be set for docker-build-web' && exit 1)
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --load -f docker/web.Dockerfile \
		--build-arg VITE_BACKEND_BASE_URL="$(VITE_BACKEND_BASE_URL)" \
		--build-arg VITE_PRODUCT_NAME="$(VITE_PRODUCT_NAME)" \
		--build-arg VITE_ENABLE_EMAIL_AUTH="$(if $(VITE_ENABLE_EMAIL_AUTH),$(VITE_ENABLE_EMAIL_AUTH),true)" \
		-t $(DOCKER_WEB_IMAGE) .

docker-build: docker-build-api docker-build-worker docker-build-schedulers docker-build-web

docker-push-api:
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --push -f docker/api.Dockerfile -t $(DOCKER_API_IMAGE) .

docker-push-worker:
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --push -f docker/worker.Dockerfile -t $(DOCKER_WORKER_IMAGE) .

docker-push-schedulers:
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --push -f docker/schedulers.Dockerfile -t $(DOCKER_SCHEDULERS_IMAGE) .

docker-push-web:
	@test -n "$(VITE_BACKEND_BASE_URL)" || (echo 'VITE_BACKEND_BASE_URL must be set for docker-push-web' && exit 1)
	@test -n "$(VITE_PRODUCT_NAME)" || (echo 'VITE_PRODUCT_NAME must be set for docker-push-web' && exit 1)
	docker buildx build --platform $(DOCKER_BUILD_PLATFORM) --push -f docker/web.Dockerfile \
		--build-arg VITE_BACKEND_BASE_URL="$(VITE_BACKEND_BASE_URL)" \
		--build-arg VITE_PRODUCT_NAME="$(VITE_PRODUCT_NAME)" \
		--build-arg VITE_ENABLE_EMAIL_AUTH="$(if $(VITE_ENABLE_EMAIL_AUTH),$(VITE_ENABLE_EMAIL_AUTH),true)" \
		-t $(DOCKER_WEB_IMAGE) .

docker-push: docker-push-api docker-push-worker docker-push-schedulers docker-push-web

docker-run-api:
	docker run --rm --init -p 8000:8000 --env-file $(BACKEND_DIR)/.env $(DOCKER_API_IMAGE)

docker-run-worker-auth-audit-export:
	docker run --rm --init --env-file $(BACKEND_DIR)/.env \
		-e WORKER_MODULE=app.workers.entrypoints.auth_audit_export \
		$(DOCKER_WORKER_IMAGE)

docker-run-worker-sample-wait-blob:
	docker run --rm --init --env-file $(BACKEND_DIR)/.env \
		-e WORKER_MODULE=app.workers.entrypoints.sample_wait_blob \
		$(DOCKER_WORKER_IMAGE)

docker-run-schedulers-sessions:
	docker run --rm --init --env-file $(BACKEND_DIR)/.env \
		-e SCHEDULERS_COMMAND=sessions-cleanup \
		$(DOCKER_SCHEDULERS_IMAGE)

docker-run-schedulers-audit:
	docker run --rm --init --env-file $(BACKEND_DIR)/.env \
		-e SCHEDULERS_COMMAND=audit-cleanup \
		$(DOCKER_SCHEDULERS_IMAGE)

docker-run-schedulers-jobs-dry-run:
	docker run --rm --init --env-file $(BACKEND_DIR)/.env \
		-e SCHEDULERS_COMMAND="jobs-cleanup --dry-run" \
		$(DOCKER_SCHEDULERS_IMAGE)

docker-run-web:
	docker run --rm -p 3000:3000 $(DOCKER_WEB_IMAGE)

# ------------------------------
# Combined runtime targets
# ------------------------------
.PHONY: install env ci up up-api up-web up-worker up-worker-auth-audit-export up-worker-sample-wait-blob dev dev-api dev-web dev-worker dev-worker-auth-audit-export dev-worker-sample-wait-blob

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

ci: install frontend-ci backend-ci

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

# `up-worker-auth-audit-export` は本番相当設定で監査ログ export worker を起動する用途。
up-worker-auth-audit-export: env backend-install
	uv --directory $(BACKEND_DIR) run python -m app.workers.entrypoints.auth_audit_export

# `up-worker-sample-wait-blob` は本番相当設定で sample worker を起動する用途。
up-worker-sample-wait-blob: env backend-install
	uv --directory $(BACKEND_DIR) run python -m app.workers.entrypoints.sample_wait_blob

# `up-worker` は本番相当設定で各ジョブ種別 worker を同時起動する用途。
up-worker:
	@trap 'kill 0' INT TERM EXIT; \
	( $(MAKE) up-worker-auth-audit-export ) & \
	( $(MAKE) up-worker-sample-wait-blob ) & \
	wait

# `up` は `up-api` / `up-web` / `up-worker` を別サブシェルで同時起動する用途。
up:
	@trap 'kill 0' INT TERM EXIT; \
	( $(MAKE) up-api ) & \
	( $(MAKE) up-web ) & \
	( $(MAKE) up-worker ) & \
	wait

# `dev-api` はホットリロード有効（uvicorn --reload）で API 開発を行う用途。
dev-api: env backend-install
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log

# `dev-web` はホットリロード有効（pnpm run dev）で Web 開発を行う用途。
dev-web: env frontend-install
	cd $(FRONTEND_DIR) && pnpm run dev

# `dev-worker-auth-audit-export` は開発時に監査ログ export worker を起動する用途。
dev-worker-auth-audit-export: env backend-install
	uv --directory $(BACKEND_DIR) run python -m app.workers.entrypoints.auth_audit_export

# `dev-worker-sample-wait-blob` は開発時に sample worker を起動する用途。
dev-worker-sample-wait-blob: env backend-install
	uv --directory $(BACKEND_DIR) run python -m app.workers.entrypoints.sample_wait_blob

# `dev-worker` は開発時に各ジョブ種別 worker を同時起動する用途。
dev-worker:
	@trap 'kill 0' INT TERM EXIT; \
	( $(MAKE) dev-worker-auth-audit-export ) & \
	( $(MAKE) dev-worker-sample-wait-blob ) & \
	wait

# `dev` は `dev-api` / `dev-web` / `dev-worker` を別サブシェルで同時起動する用途。
dev:
	@trap 'kill 0' INT TERM EXIT; \
	( $(MAKE) dev-api ) & \
	( $(MAKE) dev-web ) & \
	( $(MAKE) dev-worker ) & \
	wait
