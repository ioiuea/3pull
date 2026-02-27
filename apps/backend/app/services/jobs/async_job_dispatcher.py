"""非同期ジョブ dispatch サービス."""

from __future__ import annotations

from celery.result import AsyncResult

from app.adapters.queue import enqueue_task


def dispatch_async_job(
    *,
    task_name: str,
    kwargs: dict[str, object],
    queue_name: str,
    countdown_seconds: int = 0,
) -> AsyncResult:
    """Celery キューへジョブ投入する."""
    return enqueue_task(
        task_name=task_name,
        kwargs=kwargs,
        queue=queue_name,
        countdown_seconds=countdown_seconds,
    )
