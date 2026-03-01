from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.workers.runtime import WorkerRuntimeConfig, run_worker_loop


class _LoopStopped(RuntimeError):
    """テスト用に無限ループを抜けるための例外."""


class _RetryableError(RuntimeError):
    """一時失敗のテスト用例外."""


class _PermanentError(RuntimeError):
    """恒久失敗のテスト用例外."""


def _make_message() -> object:
    return type(
        "FakeMessage",
        (),
        {
            "body": [
                b'{"job_id":"job-1","job_type":"auth_audit_export",'
                b'"task_name":"jobs.auth_audit_export","requested_at":null}'
            ],
            "message_id": "msg-1",
            "delivery_count": 2,
        },
    )()


def test_run_worker_loop_completes_message_on_success(monkeypatch) -> None:
    # 目的: handler 成功時に complete_message が呼ばれることを保証する。
    # 条件: execute が正常終了する handler spec と 1 件メッセージを返す receiver を与える。
    # 期待値: complete_message が呼ばれ、他の ack は呼ばれない。
    state: dict[str, object] = {}

    class _FakeReceiver:
        receive_count = 0

        def receive_messages(self, *, max_message_count: int, max_wait_time: int):
            type(self).receive_count += 1
            if type(self).receive_count > 1:
                raise _LoopStopped()
            return [_make_message()]

        def complete_message(self, message: object) -> None:
            state["action"] = "complete"

        def abandon_message(self, message: object) -> None:
            state["action"] = "abandon"

        def dead_letter_message(self, message: object, **kwargs) -> None:
            state["action"] = "dead_letter"

    @contextmanager
    def _fake_get_receiver(*, queue_name: str, max_wait_time: int):
        yield _FakeReceiver()

    async def _execute(*, job_id: str) -> None:
        state["job_id"] = job_id

    async def _mark_failed(*, job_id: str, error_message: str) -> None:
        state["mark_failed"] = (job_id, error_message)

    spec = SimpleNamespace(
        execute=_execute,
        mark_failed=_mark_failed,
        retryable_errors=(_RetryableError,),
        permanent_errors=(_PermanentError,),
        canceled_errors=(RuntimeError,),
    )

    monkeypatch.setattr("app.workers.runtime.get_settings", lambda: type("S", (), {"api_log_level": "INFO"})())
    monkeypatch.setattr("app.workers.runtime.configure_logging", lambda **kwargs: None)
    monkeypatch.setattr("app.workers.runtime.get_worker_handler", lambda job_type: spec)
    monkeypatch.setattr("app.workers.runtime.get_service_bus_receiver", _fake_get_receiver)

    with pytest.raises(_LoopStopped):
        run_worker_loop(
            config=WorkerRuntimeConfig(
                queue_name="auth-audit-export",
                expected_job_type="auth_audit_export",
            )
        )

    assert state["action"] == "complete"
    assert state["job_id"] == "job-1"
    assert "mark_failed" not in state


def test_run_worker_loop_abandons_message_on_retryable_error(monkeypatch) -> None:
    # 目的: retryable エラー時に abandon_message が呼ばれることを保証する。
    # 条件: execute が retryable 例外を送出する。
    # 期待値: abandon_message が呼ばれ、dead-letter は呼ばれない。
    state: dict[str, object] = {}

    class _FakeReceiver:
        def receive_messages(self, *, max_message_count: int, max_wait_time: int):
            return [_make_message()]

        def complete_message(self, message: object) -> None:
            state["action"] = "complete"

        def abandon_message(self, message: object) -> None:
            state["action"] = "abandon"
            raise _LoopStopped()

        def dead_letter_message(self, message: object, **kwargs) -> None:
            state["action"] = "dead_letter"

    @contextmanager
    def _fake_get_receiver(*, queue_name: str, max_wait_time: int):
        yield _FakeReceiver()

    async def _execute(*, job_id: str) -> None:
        raise _RetryableError("temporary")

    async def _mark_failed(*, job_id: str, error_message: str) -> None:
        state["mark_failed"] = (job_id, error_message)

    spec = SimpleNamespace(
        execute=_execute,
        mark_failed=_mark_failed,
        retryable_errors=(_RetryableError,),
        permanent_errors=(_PermanentError,),
        canceled_errors=(RuntimeError,),
    )

    monkeypatch.setattr("app.workers.runtime.get_settings", lambda: type("S", (), {"api_log_level": "INFO"})())
    monkeypatch.setattr("app.workers.runtime.configure_logging", lambda **kwargs: None)
    monkeypatch.setattr("app.workers.runtime.get_worker_handler", lambda job_type: spec)
    monkeypatch.setattr("app.workers.runtime.get_service_bus_receiver", _fake_get_receiver)

    with pytest.raises(_LoopStopped):
        run_worker_loop(
            config=WorkerRuntimeConfig(
                queue_name="auth-audit-export",
                expected_job_type="auth_audit_export",
            )
        )

    assert state["action"] == "abandon"
    assert "mark_failed" not in state


def test_run_worker_loop_dead_letters_message_on_permanent_error(monkeypatch) -> None:
    # 目的: permanent エラー時に mark_failed の後で dead_letter_message が呼ばれることを保証する。
    # 条件: execute が permanent 例外を送出する。
    # 期待値: mark_failed と dead_letter が呼ばれる。
    state: dict[str, object] = {}

    class _FakeReceiver:
        def receive_messages(self, *, max_message_count: int, max_wait_time: int):
            return [_make_message()]

        def complete_message(self, message: object) -> None:
            state["action"] = "complete"

        def abandon_message(self, message: object) -> None:
            state["action"] = "abandon"

        def dead_letter_message(self, message: object, **kwargs) -> None:
            state["action"] = "dead_letter"
            state["dead_letter_reason"] = kwargs["reason"]
            raise _LoopStopped()

    @contextmanager
    def _fake_get_receiver(*, queue_name: str, max_wait_time: int):
        yield _FakeReceiver()

    async def _execute(*, job_id: str) -> None:
        raise _PermanentError("broken")

    async def _mark_failed(*, job_id: str, error_message: str) -> None:
        state["mark_failed"] = (job_id, error_message)

    spec = SimpleNamespace(
        execute=_execute,
        mark_failed=_mark_failed,
        retryable_errors=(_RetryableError,),
        permanent_errors=(_PermanentError,),
        canceled_errors=(RuntimeError,),
    )

    monkeypatch.setattr("app.workers.runtime.get_settings", lambda: type("S", (), {"api_log_level": "INFO"})())
    monkeypatch.setattr("app.workers.runtime.configure_logging", lambda **kwargs: None)
    monkeypatch.setattr("app.workers.runtime.get_worker_handler", lambda job_type: spec)
    monkeypatch.setattr("app.workers.runtime.get_service_bus_receiver", _fake_get_receiver)

    with pytest.raises(_LoopStopped):
        run_worker_loop(
            config=WorkerRuntimeConfig(
                queue_name="auth-audit-export",
                expected_job_type="auth_audit_export",
            )
        )

    assert state["action"] == "dead_letter"
    assert state["dead_letter_reason"] == "permanent_failure"
    assert state["mark_failed"] == ("job-1", "broken")
