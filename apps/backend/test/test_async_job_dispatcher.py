from __future__ import annotations

from app.services.jobs.async_job_dispatcher import dispatch_async_job


def test_dispatch_async_job_delegates_to_message_sender(monkeypatch) -> None:
    # 目的: service 層が queue adapter へ正しい引数で委譲する契約を守る。
    # 条件: enqueue_async_job_message をモックし、dispatch_async_job を実行する。
    # 期待値: task_name/kwargs/queue/countdown_seconds が欠落なく渡される。
    captured: dict[str, object] = {}

    def _fake_enqueue_async_job_message(*, task_name, kwargs, queue, countdown_seconds):
        captured["task_name"] = task_name
        captured["kwargs"] = kwargs
        captured["queue"] = queue
        captured["countdown_seconds"] = countdown_seconds
        return "ok"

    # dispatch_async_job 自身の委譲だけを検証したいため、
    # 実際の Service Bus 送信処理は fake 関数へ差し替える。
    monkeypatch.setattr(
        "app.services.jobs.async_job_dispatcher.enqueue_async_job_message",
        _fake_enqueue_async_job_message,
    )

    result = dispatch_async_job(
        task_name="jobs.auth_audit_export",
        kwargs={"job_id": "job-1"},
        queue_name="auth_audit_exports",
        countdown_seconds=3,
    )

    assert result == "ok"
    assert captured == {
        "task_name": "jobs.auth_audit_export",
        "kwargs": {"job_id": "job-1"},
        "queue": "auth_audit_exports",
        "countdown_seconds": 3,
    }
