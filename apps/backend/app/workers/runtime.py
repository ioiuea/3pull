"""Service Bus 用 worker ランタイム.

Service Bus からメッセージを受信し、job_type に対応する job 実装を実行して、
結果に応じて complete / abandon / dead-letter を行う共通実行部。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.adapters.queue.service_bus_client import get_service_bus_receiver
from app.core.logging.config import configure_logging, get_logger
from app.core.settings import get_settings
from app.workers.job_registry import WorkerHandlerSpec, get_worker_handler
from app.workers.messages import AsyncJobQueueMessage

logger = get_logger(__name__)


@dataclass(frozen=True)
class WorkerRuntimeConfig:
    """worker ランタイム設定."""

    queue_name: str
    expected_job_type: str
    poll_wait_seconds: int = 5


def _extract_message_id(message: object) -> str | None:
    # SDK の具体型に強く依存しすぎないよう、最低限の属性だけを取り出す。
    raw = getattr(message, "message_id", None)
    return str(raw) if raw is not None else None


def _extract_delivery_count(message: object) -> int | None:
    # delivery_count は SDK 実装差で型がぶれることがあるため、ここで吸収する。
    raw = getattr(message, "delivery_count", None)
    if isinstance(raw, int):
        return raw
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


async def _handle_with_spec(
    *,
    spec: WorkerHandlerSpec,
    queue_message: AsyncJobQueueMessage,
) -> None:
    # handler 側で分類済みの例外だけをそのまま runtime へ返し、
    # ack / abandon / dead-letter の判断は runtime 側に集約する。
    try:
        await spec.execute(job_id=queue_message.job_id)
    except spec.retryable_errors:
        raise
    except spec.permanent_errors:
        raise
    except spec.canceled_errors:
        raise


def run_worker_loop(*, config: WorkerRuntimeConfig) -> None:
    """
    指定キューを継続監視し、受信メッセージを順次処理する.
    """
    settings = get_settings()
    configure_logging(level=settings.api_log_level)

    logger.info(
        "worker.loop.started",
        queue_name=config.queue_name,
        expected_job_type=config.expected_job_type,
        poll_wait_seconds=config.poll_wait_seconds,
    )
    spec = get_worker_handler(config.expected_job_type)

    # receiver はループの外で開きっぱなしにする。
    # 毎回開閉すると接続コストとログノイズが増えるため、常駐 worker らしく扱う。
    with get_service_bus_receiver(
        queue_name=config.queue_name,
        max_wait_time=config.poll_wait_seconds,
    ) as receiver:
        while True:
            # 1 Pod 1 メッセージ直列処理の方針なので、常に 1 件ずつ受け取る。
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=5)

            if not messages:
                continue

            message = messages[0]
            message_id = _extract_message_id(message)
            delivery_count = _extract_delivery_count(message)
            queue_message: AsyncJobQueueMessage | None = None

            try:
                queue_message = AsyncJobQueueMessage.from_received_message(message)
                if queue_message.job_type != config.expected_job_type:
                    # 別種ジョブを誤って処理しないため、
                    # 起動時設定とメッセージ種別を必ず照合する。
                    raise RuntimeError(
                        "Message job_type does not match worker configuration"
                    )

                logger.info(
                    "worker.message.received",
                    queue_name=config.queue_name,
                    message_id=message_id,
                    delivery_count=delivery_count,
                    **queue_message.to_log_dict(),
                )

                asyncio.run(
                    _handle_with_spec(
                        spec=spec,
                        queue_message=queue_message,
                    )
                )
                receiver.complete_message(message)
                logger.info(
                    "worker.message.completed",
                    queue_name=config.queue_name,
                    message_id=message_id,
                    delivery_count=delivery_count,
                    **queue_message.to_log_dict(),
                )
            except spec.retryable_errors as exc:
                # 一時エラーは abandon して再配送に任せる。
                receiver.abandon_message(message)
                logger.warning(
                    "worker.message.abandoned",
                    queue_name=config.queue_name,
                    message_id=message_id,
                    delivery_count=delivery_count,
                    error=str(exc),
                )
            except spec.permanent_errors as exc:
                if queue_message is None:
                    queue_message = AsyncJobQueueMessage.from_received_message(message)
                # 恒久失敗は DB も failed に寄せた上で DLQ へ送る。
                asyncio.run(
                    spec.mark_failed(
                        job_id=queue_message.job_id,
                        error_message=str(exc),
                    )
                )
                receiver.dead_letter_message(
                    message,
                    reason="permanent_failure",
                    error_description=str(exc),
                )
                logger.warning(
                    "worker.message.dead_lettered",
                    queue_name=config.queue_name,
                    message_id=message_id,
                    delivery_count=delivery_count,
                    error=str(exc),
                    **queue_message.to_log_dict(),
                )
            except spec.canceled_errors:
                if queue_message is None:
                    queue_message = AsyncJobQueueMessage.from_received_message(message)
                # キャンセル済みや終了済みのジョブは、再試行せず正常消化する。
                receiver.complete_message(message)
                logger.info(
                    "worker.message.skipped",
                    queue_name=config.queue_name,
                    message_id=message_id,
                    delivery_count=delivery_count,
                    reason="canceled_or_finalized",
                    **queue_message.to_log_dict(),
                )
            except Exception as exc:  # pragma: no cover
                # 分類漏れの例外は、まず一時失敗として再試行に寄せる。
                receiver.abandon_message(message)
                logger.exception(
                    "worker.message.failed",
                    queue_name=config.queue_name,
                    message_id=message_id,
                    delivery_count=delivery_count,
                    error=str(exc),
                )
