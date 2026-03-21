"""非同期ジョブ成果物の整理と stuck `running` ジョブの `failed` 化を行う cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import perf_counter
from uuid import UUID

from app.adapters.sql.session import get_session_factory
from app.adapters.storage import delete_blob
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.repositories.jobs import (
    count_async_job_artifacts_by_job_id,
    count_expired_async_job_artifacts,
    count_stale_running_async_jobs,
    delete_async_job_artifacts_by_ids,
    list_expired_async_job_artifacts,
    list_stale_running_async_jobs,
    mark_async_jobs_expired_by_ids,
    mark_async_jobs_failed_by_ids,
)
from app.schedulers.cleanup.helpers import CleanupResult

logger = get_logger(__name__)


def _build_running_timeout_error_message(*, timeout_seconds: int) -> str:
    return (
        "Job exceeded running timeout and was marked failed by cleanup "
        f"({timeout_seconds} seconds)"
    )


async def run_jobs_cleanup(*, dry_run: bool, batch_size: int) -> CleanupResult:
    start = perf_counter()
    settings = get_settings()

    if not settings.async_jobs_enabled:
        return CleanupResult(
            job_name="jobs_cleanup",
            status="disabled",
            deleted_count=0,
            duration_ms=(perf_counter() - start) * 1000,
        )

    run_at = datetime.now(timezone.utc)
    stale_started_before = run_at - timedelta(
        seconds=settings.async_job_running_timeout_seconds
    )
    session_factory = get_session_factory()

    with session_factory.begin() as session:
        expired_artifact_target_count = count_expired_async_job_artifacts(
            session,
            expires_before=run_at,
        )
        stale_running_target_count = count_stale_running_async_jobs(
            session,
            started_before=stale_started_before,
        )

    target_count = expired_artifact_target_count + stale_running_target_count

    logger.info(
        "cleanup.jobs.criteria",
        run_at=run_at.isoformat(),
        delete_before_expires_at=run_at.isoformat(),
        stale_started_before=stale_started_before.isoformat(),
        expired_artifact_target_count=expired_artifact_target_count,
        stale_running_target_count=stale_running_target_count,
        total_target_count=target_count,
        dry_run=dry_run,
        batch_size=batch_size,
    )

    if dry_run:
        return CleanupResult(
            job_name="jobs_cleanup",
            status="dry_run",
            deleted_count=target_count,
            duration_ms=(perf_counter() - start) * 1000,
        )

    deleted_artifact_rows = 0
    deleted_blob_count = 0
    failed_blob_count = 0
    expired_job_count = 0
    failed_stale_running_count = 0

    while True:
        with session_factory.begin() as session:
            candidates = list_expired_async_job_artifacts(
                session,
                expires_before=run_at,
                limit=batch_size,
                offset=0,
            )

        if not candidates:
            break

        deleted_artifact_ids: list[UUID] = []
        affected_job_ids: set[UUID] = set()
        for artifact in candidates:
            try:
                delete_blob(blob_path=artifact.blob_path)
                deleted_blob_count += 1
                deleted_artifact_ids.append(artifact.id)
                affected_job_ids.add(artifact.job_id)
            except Exception as exc:  # pragma: no cover
                failed_blob_count += 1
                logger.warning(
                    "cleanup.jobs.blob_delete_failed",
                    artifact_id=str(artifact.id),
                    job_id=str(artifact.job_id),
                    blob_path=artifact.blob_path,
                    error=str(exc),
                )

        if not deleted_artifact_ids:
            logger.warning(
                "cleanup.jobs.no_progress",
                run_at=run_at.isoformat(),
                candidate_count=len(candidates),
                failed_blob_count=failed_blob_count,
                message=(
                    "No artifacts could be deleted in this batch; "
                    "stopping to avoid infinite retry loop"
                ),
            )
            break

        with session_factory.begin() as session:
            deleted = delete_async_job_artifacts_by_ids(
                session,
                artifact_ids=deleted_artifact_ids,
            )
            deleted_artifact_rows += deleted

            job_ids_to_expire: list[UUID] = []
            for job_id in affected_job_ids:
                remain = count_async_job_artifacts_by_job_id(
                    session,
                    job_id=job_id,
                )
                if remain == 0:
                    job_ids_to_expire.append(job_id)
            expired_job_count += mark_async_jobs_expired_by_ids(
                session,
                job_ids=job_ids_to_expire,
                expired_at=run_at,
            )

        if len(candidates) < batch_size:
            break

    stale_running_error_message = _build_running_timeout_error_message(
        timeout_seconds=settings.async_job_running_timeout_seconds,
    )

    while True:
        with session_factory.begin() as session:
            stale_jobs = list_stale_running_async_jobs(
                session,
                started_before=stale_started_before,
                limit=batch_size,
                offset=0,
            )

        if not stale_jobs:
            break

        with session_factory.begin() as session:
            failed_stale_running_count += mark_async_jobs_failed_by_ids(
                session,
                job_ids=[job.id for job in stale_jobs],
                failed_at=run_at,
                error_message=stale_running_error_message,
            )

        if len(stale_jobs) < batch_size:
            break

    logger.info(
        "cleanup.jobs.deleted",
        run_at=run_at.isoformat(),
        stale_started_before=stale_started_before.isoformat(),
        total_target_count=target_count,
        batch_size=batch_size,
        deleted_artifact_rows=deleted_artifact_rows,
        deleted_blob_count=deleted_blob_count,
        failed_blob_count=failed_blob_count,
        expired_job_count=expired_job_count,
        failed_stale_running_count=failed_stale_running_count,
    )
    return CleanupResult(
        job_name="jobs_cleanup",
        status="success",
        deleted_count=deleted_artifact_rows + failed_stale_running_count,
        duration_ms=(perf_counter() - start) * 1000,
    )
