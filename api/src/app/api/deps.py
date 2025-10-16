"""
依存性注入（DI）モジュール

このモジュールはFastAPIのDependsで使用するリポジトリインスタンスを提供します。
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.repositories.base import (
    ChatThreadRepositoryProtocol,
    FolderRepositoryProtocol,
)
from app.repositories.sqlite import (
    SQLiteChatThreadRepository,
    SQLiteFolderRepository,
)


async def get_folder_repo(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> AsyncGenerator[FolderRepositoryProtocol, None]:
    """
    フォルダリポジトリを取得

    環境変数DB_BACKENDに応じて適切なリポジトリ実装を返します。

    Args:
        session: データベースセッション

    Yields:
        FolderRepositoryProtocol: フォルダリポジトリ

    Raises:
        ValueError: 未知のDB_BACKENDが指定された場合
    """
    if settings.db_backend == "sqlite":
        yield SQLiteFolderRepository(session)
    elif settings.db_backend == "cosmos":
        raise NotImplementedError("Cosmos DB implementation coming in Step 5")
    else:
        raise ValueError(f"Unknown DB_BACKEND: {settings.db_backend}")


async def get_chatthread_repo(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> AsyncGenerator[ChatThreadRepositoryProtocol, None]:
    """
    チャットスレッドリポジトリを取得

    環境変数DB_BACKENDに応じて適切なリポジトリ実装を返します。

    Args:
        session: データベースセッション

    Yields:
        ChatThreadRepositoryProtocol: チャットスレッドリポジトリ

    Raises:
        ValueError: 未知のDB_BACKENDが指定された場合
    """
    if settings.db_backend == "sqlite":
        yield SQLiteChatThreadRepository(session)
    elif settings.db_backend == "cosmos":
        raise NotImplementedError("Cosmos DB implementation coming in Step 5")
    else:
        raise ValueError(f"Unknown DB_BACKEND: {settings.db_backend}")
