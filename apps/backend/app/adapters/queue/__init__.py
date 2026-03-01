"""
キュー接続アダプターパッケージ.

- Service Bus クライアント生成
- メッセージ enqueue 共通処理
"""

from app.adapters.queue.message_sender import EnqueueResult, enqueue_async_job_message
from app.adapters.queue.service_bus_client import get_service_bus_sender

__all__ = [
    "get_service_bus_sender",
    "EnqueueResult",
    "enqueue_async_job_message",
]
