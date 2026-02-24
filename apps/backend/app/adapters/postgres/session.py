"""
psycopg v3 を用いた非同期 SQLAlchemy エンジンと FastAPI 依存.

- DATABASE_URL（例: postgresql+psycopg://...）を使用する
- get_session() は UoW としてトランザクション範囲を提供する
- Router/Service で commit()/rollback() を呼ばない方針を強制する
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def _resolve_database_url() -> str:
    """
    DATABASE_URL を解決し、未設定時は明示的に失敗させる.

    Returns:
        str: SQLAlchemy 用 DATABASE_URL

    Raises:
        RuntimeError: DATABASE_URL が未設定の場合
    """
    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        logger.error("DATABASE_URL is not set (e.g. postgresql+psycopg://...)")
        raise RuntimeError("DATABASE_URL is not set")
    return database_url


settings = get_settings()
# インポート時に DB URL を解決する（未設定時は早期に失敗させる）。
DATABASE_URL = _resolve_database_url()

# 非同期エンジン（psycopg v3）。
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)

# セッションファクトリ。
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    非同期セッションファクトリを返す.

    Returns:
        async_sessionmaker[AsyncSession]: セッションファクトリ
    """
    return SessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    トランザクション（UoW）内で AsyncSession を yield する FastAPI 依存.

    Yields:
        AsyncSession: `async with session.begin()` 範囲内のアクティブセッション
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # begin() 文脈で成功時 commit / 例外時 rollback を一元化する。
        async with session.begin():
            yield session


async def dispose_engine() -> None:
    """
    アプリ停止時にエンジン接続プールを解放する.
    """
    await engine.dispose()
