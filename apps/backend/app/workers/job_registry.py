"""job_type ごとの job 実装登録表."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass

from app.workers.jobs import (
    JobCanceledExportError,
    JobCanceledSampleError,
    PermanentExportError,
    PermanentSampleError,
    RetryableExportError,
    RetryableSampleError,
    execute_auth_audit_export_job,
    execute_sample_wait_blob_job,
    mark_auth_audit_export_failed,
    mark_sample_wait_blob_failed,
)

ExecuteFunc = Callable[..., Coroutine[object, object, object]]
MarkFailedFunc = Callable[..., Coroutine[object, object, None]]


@dataclass(frozen=True)
class WorkerHandlerSpec:
    """worker 実行ハンドラ定義."""

    job_type: str
    # 実処理本体。job_id を受けて、必要なら戻り値を返す。
    execute: ExecuteFunc
    # 恒久失敗時に DB を failed へ寄せるための補助関数。
    mark_failed: MarkFailedFunc
    # runtime は「どの例外ならどう ACK するか」だけをこの分類で判断する。
    retryable_errors: tuple[type[Exception], ...]
    permanent_errors: tuple[type[Exception], ...]
    canceled_errors: tuple[type[Exception], ...]


_HANDLERS: dict[str, WorkerHandlerSpec] = {
    "auth_audit_export": WorkerHandlerSpec(
        job_type="auth_audit_export",
        execute=execute_auth_audit_export_job,
        mark_failed=mark_auth_audit_export_failed,
        retryable_errors=(RetryableExportError,),
        permanent_errors=(PermanentExportError,),
        canceled_errors=(JobCanceledExportError,),
    ),
    "sample_wait_blob": WorkerHandlerSpec(
        job_type="sample_wait_blob",
        execute=execute_sample_wait_blob_job,
        mark_failed=mark_sample_wait_blob_failed,
        retryable_errors=(RetryableSampleError,),
        permanent_errors=(PermanentSampleError,),
        canceled_errors=(JobCanceledSampleError,),
    ),
}


def get_worker_handler(job_type: str) -> WorkerHandlerSpec:
    """job_type から handler を返す."""
    # job_type ごとの分岐を runtime 本体に散らさず、この registry に閉じ込める。
    if job_type not in _HANDLERS:
        raise RuntimeError(f"Unsupported job_type: {job_type}")
    return _HANDLERS[job_type]
