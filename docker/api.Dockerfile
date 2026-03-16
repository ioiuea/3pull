# ================================================================
# Backend API (FastAPI) — Dockerfile
# - Python 3.12
# - `apps/backend` の依存を uv で固定インストール
# - 実行時は gunicorn + uvicorn worker で API を起動
# ================================================================

# -------------------------
# builder: 依存解決専用ステージ
# -------------------------
# ここでは Python 依存のインストールだけを行い、
# 実行時イメージへは「完成済みの仮想環境」だけを渡す。
FROM python:3.12-slim-bookworm AS builder

ENV UV_PROJECT_ENVIRONMENT=/workspace/apps/backend/.venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /workspace

# uv バイナリだけを公式イメージから持ち込む。
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

# 依存解決に必要なファイルだけ先にコピーして、キャッシュを効かせる。
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./apps/backend/

# 本番イメージなので dev 依存は入れない。
RUN uv sync --frozen --no-dev --project ./apps/backend

# -------------------------
# runtime: API 実行ステージ
# -------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/workspace/apps/backend/.venv/bin:${PATH}" \
    PORT=8000 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=1 \
    GUNICORN_TIMEOUT=60 \
    GUNICORN_KEEPALIVE=5

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

# builder で作成した仮想環境をそのままコピーする。
COPY --from=builder /workspace/apps/backend/.venv ./.venv

# 実行に必要な backend コードだけをコピーする。
COPY apps/backend/app ./app
COPY apps/backend/alembic ./alembic
COPY apps/backend/alembic.ini ./alembic.ini

EXPOSE 8000

# gunicorn がプロセス管理、uvicorn worker が ASGI 実行を担当する。
CMD ["sh", "-c", "exec gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} --keep-alive ${GUNICORN_KEEPALIVE}"]
