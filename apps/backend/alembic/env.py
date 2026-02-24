"""
Alembic 実行コンテキスト設定.

- app 側の pydantic-settings から DATABASE_URL を解決する
- SQLAlchemy Base.metadata を target_metadata に設定する
- autogenerate 時の型差分・デフォルト差分比較を有効化する
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.adapters.postgres.base import Base
from app.core.settings import get_settings
from app.models import load_all_models

# this is the Alembic Config object, which provides access
# to the values within the .ini file in use.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic がモデル定義を認識できるように import 副作用を明示する。
load_all_models()
target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """
    DATABASE_URL を設定から取得し、Alembic 設定へ反映する.

    Returns:
        str: SQLAlchemy 接続 URL

    Raises:
        RuntimeError: DATABASE_URL が未設定の場合
    """
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for alembic migrations")
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
