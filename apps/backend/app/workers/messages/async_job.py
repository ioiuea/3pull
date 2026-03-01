"""Service Bus 非同期ジョブの受信メッセージ定義."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class AsyncJobQueueMessage(BaseModel):
    """Service Bus 上の非同期ジョブメッセージ."""

    job_id: str
    job_type: str
    task_name: str
    requested_at: str | None = None

    @classmethod
    def from_received_message(cls, message: object) -> "AsyncJobQueueMessage":
        """
        Service Bus 受信メッセージからモデルを構築する.
        """
        raw_body = getattr(message, "body", None)
        if raw_body is None:
            raise RuntimeError("Message body is required")

        # SDK によって body の見え方が異なるため、
        # bytes / str / iterable をここで吸収する。
        if isinstance(raw_body, (bytes, bytearray)):
            body_text = bytes(raw_body).decode("utf-8")
        elif isinstance(raw_body, str):
            body_text = raw_body
        else:
            chunks: list[bytes] = []
            for chunk in raw_body:
                if isinstance(chunk, bytes):
                    chunks.append(chunk)
                elif isinstance(chunk, bytearray):
                    chunks.append(bytes(chunk))
                else:
                    chunks.append(str(chunk).encode("utf-8"))
            body_text = b"".join(chunks).decode("utf-8")

        payload = json.loads(body_text)
        if not isinstance(payload, dict):
            raise RuntimeError("Message body must be a JSON object")
        # 受信直後に Pydantic で形を固定し、以降の処理で辞書の生扱いを避ける。
        return cls.model_validate(payload)

    def to_log_dict(self) -> dict[str, Any]:
        """ログ出力用のメタ情報."""
        # 構造化ログに載せるキーをここで統一しておく。
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "task_name": self.task_name,
            "requested_at": self.requested_at,
        }
