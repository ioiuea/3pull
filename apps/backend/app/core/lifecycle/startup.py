"""
アプリケーションのライフサイクル管理.

- 起動時にログ設定を初期化する
- 起動/停止イベントを構造化ログで記録する
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging.config import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI の lifespan コンテキストを管理する.

    Args:
        app: FastAPI アプリケーションインスタンス
    """
    # 起動直後にログ基盤を初期化する。
    configure_logging()
    # どの API プレフィックスで起動したかを記録する。
    logger.info("application.startup", api_prefix=getattr(app.state, "api_prefix", None))
    try:
        yield
    finally:
        # shutdown 直前に停止ログを出力する。
        logger.info("application.shutdown", api_prefix=getattr(app.state, "api_prefix", None))
