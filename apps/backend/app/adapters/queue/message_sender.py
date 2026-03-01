"""
Service Bus メッセージ enqueue 共通処理.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from azure.servicebus import ServiceBusMessage

from app.adapters.queue.service_bus_client import get_service_bus_sender


@dataclass(frozen=True)
class EnqueueResult:
    """メッセージ送信結果."""

    queue_name: str
    task_name: str
    job_id: str


def enqueue_async_job_message(
    *,
    task_name: str,
    args: Sequence[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str | None = None,
    countdown_seconds: int = 0,
) -> EnqueueResult:
    """
    Service Bus へ非同期ジョブメッセージを送信する.
    """
    # 必要最小限の job_id ベースに固定する。
    if args:
        raise RuntimeError("Positional args are not supported for async job enqueue")
    if countdown_seconds > 0:
        raise RuntimeError("Delayed enqueue is not supported")
    if queue is None:
        raise RuntimeError("Queue name is required")
    if kwargs is None:
        raise RuntimeError("Keyword arguments are required")

    job_id_raw = kwargs.get("job_id")
    if not isinstance(job_id_raw, str) or not job_id_raw.strip():
        raise RuntimeError("job_id is required in kwargs")

    # task_name から job_type を機械的に導き、worker 側の handler 解決に使う。
    job_type = task_name.removeprefix("jobs.")
    body = json.dumps(
        {
            "job_id": job_id_raw,
            "job_type": job_type,
            "task_name": task_name,
            "requested_at": kwargs.get("requested_at"),
        }
    )
    # body が正本。application_properties には追跡しやすい最小メタ情報だけ載せる。
    message = ServiceBusMessage(
        body=body,
        content_type="application/json",
        application_properties={
            "job_id": job_id_raw,
            "task_name": task_name,
        },
    )

    with get_service_bus_sender(queue_name=queue) as sender:
        sender.send_messages(message)

    # 呼び出し元で監査ログやテストに使いやすいよう、送信結果を値で返す。
    return EnqueueResult(
        queue_name=queue,
        task_name=task_name,
        job_id=job_id_raw,
    )
