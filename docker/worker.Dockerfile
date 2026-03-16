# ================================================================
# Backend Worker (Service Bus worker) — Dockerfile
# - Python 3.12
# - `apps/backend` の依存を uv で固定インストール
# - 実行時は `app.workers.entrypoints.*` を起動
# - Queue を継続監視する常駐型コンテナとして使う
# ================================================================

# -------------------------
# builder: 依存解決専用ステージ
# -------------------------
FROM python:3.12-slim-bookworm AS builder

ENV UV_PROJECT_ENVIRONMENT=/workspace/apps/backend/.venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./apps/backend/
RUN uv sync --frozen --no-dev --project ./apps/backend

# -------------------------
# runtime: worker 実行ステージ
# -------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/backend/.venv/bin:${PATH}" \
    WORKER_MODULE=app.workers.entrypoints.auth_audit_export

WORKDIR /workspace/apps/backend

# Azure SQL + pyodbc 実行に必要な ODBC ランタイムを入れる。
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc libgssapi-krb5-2 \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /workspace/apps/backend/.venv ./.venv
COPY apps/backend/app ./app
COPY apps/backend/alembic ./alembic
COPY apps/backend/alembic.ini ./alembic.ini

# このイメージは worker 共通イメージとして使い、
# 実際にどの worker を起動するかは `WORKER_MODULE` で切り替える。
# 起動後は対象キューを監視し続けるため、Deployment などの常駐用途を想定している。
# 例:
# - app.workers.entrypoints.auth_audit_export
# - app.workers.entrypoints.sample_wait_blob
CMD ["sh", "-c", "exec python -m ${WORKER_MODULE}"]
