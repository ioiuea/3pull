"""
待機後にテスト成果物を Blob へ出力するサンプル Celery タスク.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.adapters.postgres.session import get_session_factory
from app.adapters.queue import get_celery_app
from app.adapters.storage import upload_bytes
from app.core.logging.config import configure_logging, get_logger
from app.core.settings import get_settings
from app.models.jobs.async_job import AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifactType
from app.repositories.jobs.async_job_artifact_repository import (
    create_async_job_artifact,
)
from app.repositories.jobs.async_job_repository import (
    get_async_job_by_id,
    update_async_job_status,
)

logger = get_logger(__name__)
celery_app = get_celery_app()
_SAMPLE_FILENAME_PREFIX = "sample-wait-blob"


class RetryableSampleError(RuntimeError):
    """再試行で回復する可能性があるエラー."""


class PermanentSampleError(RuntimeError):
    """再試行しても回復しないエラー."""


class JobCanceledSampleError(RuntimeError):
    """ジョブがキャンセル済みであることを表すエラー."""


def _build_blob_path(*, now_utc: datetime, job_id: str, prefix: str) -> str:
    return f"sample-jobs/{now_utc:%Y}/{now_utc:%m}/{prefix}-{job_id}.txt"


async def _mark_failed(*, job_id: str, error_message: str) -> None:
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
            if job is None:
                return
            await update_async_job_status(
                session,
                job=job,
                status=AsyncJobStatus.FAILED,
                finished_at=datetime.now(timezone.utc),
                error_message=error_message[:2048],
            )


async def _run_sample_job(*, job_id: str) -> tuple[str, int]:
    settings = get_settings()
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
            if job is None:
                raise RetryableSampleError("Sample job not found yet")
            if job.job_type != AsyncJobType.SAMPLE_WAIT_BLOB:
                raise PermanentSampleError("Invalid job type for sample task")
            if job.status == AsyncJobStatus.CANCELED:
                raise JobCanceledSampleError("Sample job was canceled before start")
            if job.status in {AsyncJobStatus.SUCCEEDED, AsyncJobStatus.EXPIRED}:
                raise PermanentSampleError("Sample job is already finalized")

            wait_seconds_raw = job.requested_payload.get("wait_seconds", 120)
            if isinstance(wait_seconds_raw, (int, float)):
                wait_seconds = int(wait_seconds_raw)
            elif isinstance(wait_seconds_raw, str):
                wait_seconds = int(wait_seconds_raw)
            else:
                raise PermanentSampleError("wait_seconds must be numeric")
            if wait_seconds < 1 or wait_seconds > 600:
                raise PermanentSampleError("wait_seconds must be between 1 and 600")

            content_raw = job.requested_payload.get("content")
            custom_content = (
                str(content_raw).strip() if isinstance(content_raw, str) else None
            )

            await update_async_job_status(
                session,
                job=job,
                status=AsyncJobStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )

    for _ in range(wait_seconds):
        await asyncio.sleep(1)
        async with session_factory() as session:
            async with session.begin():
                current = await get_async_job_by_id(session, job_id=parsed_job_id)
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
    file_size = upload_bytes(
        blob_path=blob_path,
        data=payload,
        content_type="text/plain; charset=utf-8",
    )

    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
            if job is None:
                raise PermanentSampleError("Sample job not found after upload")
            if job.status == AsyncJobStatus.CANCELED:
                raise JobCanceledSampleError("Sample job was canceled before finalize")

            await create_async_job_artifact(
                session,
                job_id=job.id,
                artifact_type=AsyncJobArtifactType.SAMPLE_WAIT_BLOB_FILE,
                container_name=settings.azure_blob_container,
                blob_path=blob_path,
                content_type="text/plain; charset=utf-8",
                file_size_bytes=file_size,
                expires_at=job.expires_at,
            )
            await update_async_job_status(
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


@celery_app.task(
    bind=True,
    name=get_settings().sample_wait_blob_task_name,
    max_retries=1,
)
def run_sample_wait_blob_job(self, job_id: str) -> None:
    """120秒待機して Blob へテキスト出力するサンプルジョブ."""
    settings = get_settings()
    configure_logging(level=settings.api_log_level)

    logger.info(
        "sample.job.started",
        job_id=job_id,
        retry_count=self.request.retries,
    )

    try:
        blob_path, file_size = asyncio.run(_run_sample_job(job_id=job_id))
    except RetryableSampleError as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(job_id=job_id, error_message=str(exc)))
            logger.exception(
                "sample.job.failed",
                job_id=job_id,
                retryable=False,
                error=str(exc),
            )
            return
        logger.warning(
            "sample.job.retry",
            job_id=job_id,
            retry_count=self.request.retries + 1,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=1)
    except PermanentSampleError as exc:
        asyncio.run(_mark_failed(job_id=job_id, error_message=str(exc)))
        logger.exception(
            "sample.job.failed",
            job_id=job_id,
            retryable=False,
            error=str(exc),
        )
        return
    except JobCanceledSampleError:
        logger.info(
            "sample.job.canceled",
            job_id=job_id,
        )
        return
    except Exception as exc:  # pragma: no cover
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(job_id=job_id, error_message=str(exc)))
            logger.exception(
                "sample.job.failed",
                job_id=job_id,
                retryable=True,
                error=str(exc),
            )
            return
        logger.warning(
            "sample.job.retry",
            job_id=job_id,
            retry_count=self.request.retries + 1,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=1)

    logger.info(
        "sample.job.succeeded",
        job_id=job_id,
        blob_path=blob_path,
        file_size_bytes=file_size,
    )
