from __future__ import annotations

import json
from contextlib import contextmanager

from app.adapters.queue.message_sender import (
    EnqueueResult,
    enqueue_async_job_message,
)


def test_enqueue_async_job_message_sends_minimum_service_bus_payload(
    monkeypatch,
) -> None:
    # 目的: Service Bus 送信時に最小メタ情報だけをメッセージ化する契約を守る。
    # 条件: sender をモックし、job_id を含む enqueue を実行する。
    # 期待値: job_id / job_type / task_name を持つ JSON が送信される。
    sent = {}

    class _FakeSender:
        def send_messages(self, message) -> None:
            sent["body"] = b"".join(message.body).decode("utf-8")
            sent["content_type"] = message.content_type
            sent["application_properties"] = dict(message.application_properties)

    @contextmanager
    def _fake_get_service_bus_sender(*, queue_name: str):
        sent["queue_name"] = queue_name
        yield _FakeSender()

    monkeypatch.setattr(
        "app.adapters.queue.message_sender.get_service_bus_sender",
        _fake_get_service_bus_sender,
    )

    result = enqueue_async_job_message(
        task_name="jobs.auth_audit_export",
        kwargs={"job_id": "job-1"},
        queue="auth-audit-export",
    )

    assert result == EnqueueResult(
        queue_name="auth-audit-export",
        task_name="jobs.auth_audit_export",
        job_id="job-1",
    )
    assert sent["queue_name"] == "auth-audit-export"
    assert sent["content_type"] == "application/json"
    assert sent["application_properties"] == {
        "job_id": "job-1",
        "task_name": "jobs.auth_audit_export",
    }
    assert json.loads(sent["body"]) == {
        "job_id": "job-1",
        "job_type": "auth_audit_export",
        "task_name": "jobs.auth_audit_export",
        "requested_at": None,
    }


def test_enqueue_async_job_message_rejects_delayed_enqueue() -> None:
    # 目的: 遅延実行未対応の方針をコード上でも強制する。
    # 条件: countdown_seconds を指定して送信を呼ぶ。
    # 期待値: RuntimeError で拒否される。
    try:
        enqueue_async_job_message(
            task_name="jobs.auth_audit_export",
            kwargs={"job_id": "job-1"},
            queue="auth-audit-export",
            countdown_seconds=1,
        )
    except RuntimeError as exc:
        assert str(exc) == "Delayed enqueue is not supported"
    else:  # pragma: no cover
        raise AssertionError("RuntimeError was not raised")
