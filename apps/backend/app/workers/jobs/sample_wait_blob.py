"""サンプル待機ジョブの Queue 非依存ハンドラ."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

from app.adapters.sql.session import get_session_factory
from app.adapters.storage import upload_bytes
from app.core.settings import get_settings
from app.models.jobs.async_job import AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifactType
from app.repositories.jobs.async_job_artifact_repository import (
    create_async_job_artifact,
)
from app.repositories.jobs.async_job_repository import (
    claim_queued_job_for_run,
    get_async_job_by_id,
    update_async_job_status,
)

_SAMPLE_FILENAME_PREFIX = "sample-wait-blob"


class RetryableSampleError(RuntimeError):
    """再試行で回復する可能性があるエラー."""


class PermanentSampleError(RuntimeError):
    """再試行しても回復しないエラー."""


class JobCanceledSampleError(RuntimeError):
    """ジョブがキャンセル済みであることを表すエラー."""


def _build_blob_path(*, now_utc: datetime, job_id: str, prefix: str) -> str:
    return f"sample-jobs/{now_utc:%Y}/{now_utc:%m}/{prefix}-{job_id}.txt"


async def mark_sample_wait_blob_failed(*, job_id: str, error_message: str) -> None:
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()
    with session_factory.begin() as session:
        job = get_async_job_by_id(session, job_id=parsed_job_id)
        if job is None:
            return
        update_async_job_status(
            session,
            job=job,
            status=AsyncJobStatus.FAILED,
            finished_at=datetime.now(timezone.utc),
            error_message=error_message[:2048],
        )


async def execute_sample_wait_blob_job(*, job_id: str) -> tuple[str, int]:
    settings = get_settings()
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()

    with session_factory.begin() as session:
        job = get_async_job_by_id(session, job_id=parsed_job_id)
        if job is None:
            raise RetryableSampleError("Sample job not found yet")
        if job.job_type != AsyncJobType.SAMPLE_WAIT_BLOB:
            raise PermanentSampleError("Invalid job type for sample task")
        if job.status == AsyncJobStatus.CANCELED:
            raise JobCanceledSampleError("Sample job was canceled before start")
        if job.status in {
            AsyncJobStatus.SUCCEEDED,
            AsyncJobStatus.FAILED,
            AsyncJobStatus.EXPIRED,
        }:
            raise JobCanceledSampleError("Sample job is already finalized")
        if job.status == AsyncJobStatus.RUNNING:
            raise RetryableSampleError("Sample job is already running")

        started_at = datetime.now(timezone.utc)
        claimed_job = claim_queued_job_for_run(
            session,
            job_id=parsed_job_id,
            started_at=started_at,
        )
        if claimed_job is None:
            current = get_async_job_by_id(session, job_id=parsed_job_id)
            if current is None:
                raise RetryableSampleError("Sample job not found during claim")
            if current.status == AsyncJobStatus.CANCELED:
                raise JobCanceledSampleError("Sample job was canceled before start")
            if current.status in {
                AsyncJobStatus.SUCCEEDED,
                AsyncJobStatus.FAILED,
                AsyncJobStatus.EXPIRED,
            }:
                raise JobCanceledSampleError("Sample job is already finalized")
            raise RetryableSampleError("Sample job could not be claimed for run")

        requested_payload = (
            claimed_job.requested_payload
            if isinstance(claimed_job.requested_payload, dict)
            else {}
        )
        wait_seconds_raw = requested_payload.get("wait_seconds", 120)
        if isinstance(wait_seconds_raw, (int, float)):
            wait_seconds = int(wait_seconds_raw)
        elif isinstance(wait_seconds_raw, str):
            wait_seconds = int(wait_seconds_raw)
        else:
            raise PermanentSampleError("wait_seconds must be numeric")
        if wait_seconds < 1 or wait_seconds > 600:
            raise PermanentSampleError("wait_seconds must be between 1 and 600")

        content_raw = requested_payload.get("content")
        custom_content = (
            str(content_raw).strip() if isinstance(content_raw, str) else None
        )

    for _ in range(wait_seconds):
        await asyncio.sleep(1)
        with session_factory.begin() as session:
            current = get_async_job_by_id(session, job_id=parsed_job_id)
            if current is None:
                raise PermanentSampleError("Sample job not found during wait")
            if current.status == AsyncJobStatus.CANCELED:
                raise JobCanceledSampleError("Sample job was canceled")

    now_utc = datetime.now(timezone.utc)
    blob_path = _build_blob_path(
        now_utc=now_utc,
        job_id=job_id,
        prefix=_SAMPLE_FILENAME_PREFIX,
    )
    text_body = (
        "\n".join(
            [
                "Sample async job completed.",
                f"job_id={job_id}",
                f"wait_seconds={wait_seconds}",
                f"completed_at={now_utc.isoformat()}",
                custom_content or "",
            ]
        ).strip()
        + "\n"
    )
    payload = text_body.encode("utf-8")
    try:
        file_size = upload_bytes(
            blob_path=blob_path,
            data=payload,
            content_type="text/plain; charset=utf-8",
        )
    except (RuntimeError, ValueError) as exc:
        raise PermanentSampleError(str(exc)) from exc
    except (ClientAuthenticationError, HttpResponseError) as exc:
        raise PermanentSampleError(str(exc)) from exc

    with session_factory.begin() as session:
        job = get_async_job_by_id(session, job_id=parsed_job_id)
        if job is None:
            raise PermanentSampleError("Sample job not found after upload")
        if job.status == AsyncJobStatus.CANCELED:
            raise JobCanceledSampleError("Sample job was canceled before finalize")

        create_async_job_artifact(
            session,
            job_id=job.id,
            artifact_type=AsyncJobArtifactType.SAMPLE_WAIT_BLOB_FILE,
            container_name=settings.azure_blob_container,
            blob_path=blob_path,
            content_type="text/plain; charset=utf-8",
            file_size_bytes=file_size,
            expires_at=job.expires_at,
        )
        update_async_job_status(
            session,
            job=job,
            status=AsyncJobStatus.SUCCEEDED,
            finished_at=now_utc,
            result_payload={
                "wait_seconds": wait_seconds,
                "file_size_bytes": file_size,
                "artifact_type": AsyncJobArtifactType.SAMPLE_WAIT_BLOB_FILE.value,
            },
            error_message=None,
        )

    return blob_path, file_size
