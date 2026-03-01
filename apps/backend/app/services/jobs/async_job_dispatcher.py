"""非同期ジョブ dispatch サービス."""

from __future__ import annotations

from app.adapters.queue import EnqueueResult, enqueue_async_job_message


def dispatch_async_job(
    *,
    task_name: str,
    kwargs: dict[str, object],
    queue_name: str,
    countdown_seconds: int = 0,
) -> EnqueueResult:
    """Service Bus キューへジョブ投入する."""
    # この層は「ジョブサービス側の入口」を揃えるための薄いラッパー。
    # 実際の Service Bus 送信処理は adapter 側に閉じ込め、API や worker からは
    # 「ジョブを投入する」という意図だけが見えるようにしている。
    return enqueue_async_job_message(
        task_name=task_name,
        kwargs=kwargs,
        queue=queue_name,
        countdown_seconds=countdown_seconds,
    )
