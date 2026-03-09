# ================================================================
# Backend Schedulers (Cron / Job) — Dockerfile
# - Python 3.12
# - `apps/backend` の依存を uv で固定インストール
# - 実行時は scheduler CLI を起動
# - 1 回だけ scheduler を実行して終了する都度実行型コンテナとして使う
# ================================================================

# -------------------------
# builder: 依存解決専用ステージ
# -------------------------
FROM python:3.12-slim AS builder

ENV UV_PROJECT_ENVIRONMENT=/workspace/apps/backend/.venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./apps/backend/
RUN uv sync --frozen --no-dev --project ./apps/backend

# -------------------------
# runtime: schedulers 実行ステージ
# -------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/backend/.venv/bin:${PATH}" \
    SCHEDULERS_COMMAND=sessions

WORKDIR /workspace/apps/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /workspace/apps/backend/.venv ./.venv
COPY apps/backend/app ./app
COPY apps/backend/alembic ./alembic
COPY apps/backend/alembic.ini ./alembic.ini

# このイメージは CronJob / Job から共通で使う。
# `SCHEDULERS_COMMAND` にサブコマンドを入れて切り替える。
# 指定した scheduler を 1 回実行したらプロセスは終了するため、定期実行を前提にしている。
# 例:
# - sessions
# - audit
# - jobs
# - jobs --dry-run
CMD ["sh", "-c", "exec python -m app.schedulers.scheduler_cleanup ${SCHEDULERS_COMMAND:-sessions}"]
