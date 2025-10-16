"""
データベース接続管理

このモジュールはSQLiteデータベースへの非同期接続を管理します。
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _on_connect(dbapi_conn: Any, connection_record: Any) -> None:  # noqa: ARG001
    """接続時にPRAGMA設定を適用"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_engine() -> AsyncEngine:
    """
    非同期SQLiteエンジンを作成する

    WALモードと外部キー制約を有効化したSQLiteエンジンを返します。

    Returns:
        AsyncEngine: 非同期SQLAlchemyエンジン
    """
    connect_args: dict[str, Any] = {
        "check_same_thread": False,
    }

    engine = create_async_engine(
        settings.db_uri,
        echo=settings.debug,
        future=True,
        poolclass=NullPool,
        connect_args=connect_args,
    )

    event.listen(engine.sync_engine, "connect", _on_connect)

    return engine


engine = create_engine()
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    データベースセッションを取得する

    FastAPIのDependsで使用するための非同期ジェネレータです。

    Yields:
        AsyncSession: 非同期SQLAlchemyセッション

    Example:
        ```python
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            pass
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
