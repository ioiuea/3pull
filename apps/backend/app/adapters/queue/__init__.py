"""
キュー接続アダプターパッケージ.

- Celery アプリ初期化
- タスク enqueue 共通処理
"""

from app.adapters.queue.celery_app import get_celery_app, get_redis_client, ping_redis
from app.adapters.queue.task_dispatcher import enqueue_task

__all__ = [
    "get_celery_app",
    "get_redis_client",
    "ping_redis",
    "enqueue_task",
]
