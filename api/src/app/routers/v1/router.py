"""
API v1 ルーター

このモジュールはAPI v1の全エンドポイントをまとめます。
"""

from fastapi import APIRouter

from app.routers.v1 import chat_threads, folders
from app.routers.v1.endpoints import health, items

router = APIRouter()

router.include_router(health.router)
router.include_router(items.router)
router.include_router(folders.router)
router.include_router(chat_threads.router)


def get_v1_router() -> APIRouter:
    """
    API v1ルーターを取得

    Returns:
        APIRouter: API v1ルーター
    """
    return router
