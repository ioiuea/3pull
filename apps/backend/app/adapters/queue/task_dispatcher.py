"""
Celery タスク enqueue 共通処理.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from celery.result import AsyncResult

from app.adapters.queue.celery_app import get_celery_app


def enqueue_task(
    *,
    task_name: str,
    args: Sequence[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str | None = None,
    countdown_seconds: int = 0,
) -> AsyncResult:
    """
    汎用 Celery タスクをキュー投入する.
    """
    celery_app = get_celery_app()
    send_kwargs: dict[str, Any] = {
        "name": task_name,
        "countdown": max(countdown_seconds, 0),
    }
    if args is not None:
        send_kwargs["args"] = list(args)
    if kwargs is not None:
        send_kwargs["kwargs"] = kwargs
    if queue is not None:
        send_kwargs["queue"] = queue
    return celery_app.send_task(**send_kwargs)
