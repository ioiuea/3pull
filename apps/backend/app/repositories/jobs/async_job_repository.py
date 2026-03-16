"""AsyncJob リポジトリ."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.sql.elements import ColumnElement

from app.models.jobs.async_job import AsyncJob, AsyncJobStatus, AsyncJobType


def _serialize_payload(payload: dict[str, object] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _deserialize_payload(payload: str | None) -> dict[str, object] | None:
    if payload is None:
        return None
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _hydrate_job_payloads(job: AsyncJob) -> AsyncJob:
    set_committed_value(
        job,
        "requested_payload",
        _deserialize_payload(job.requested_payload) or {},
    )
    set_committed_value(
        job,
        "result_payload",
        _deserialize_payload(job.result_payload),
    )
    return job


def _prepare_job_payloads_for_flush(job: AsyncJob) -> None:
    requested_payload = job.requested_payload
    if isinstance(requested_payload, dict):
        set_committed_value(
            job,
            "requested_payload",
            _serialize_payload(requested_payload) or "{}",
        )

    result_payload = job.result_payload
    if isinstance(result_payload, dict):
        set_committed_value(
            job,
            "result_payload",
            _serialize_payload(result_payload),
        )


def create_async_job(
    session: Session,
    *,
    job_type: AsyncJobType,
    requested_by_user_id: UUID | None,
    queue_name: str,
    task_name: str,
    requested_payload: dict[str, object],
    expires_at: datetime | None = None,
) -> AsyncJob:
    job = AsyncJob(
        job_type=job_type,
        requested_by_user_id=requested_by_user_id,
        status=AsyncJobStatus.QUEUED,
        queue_name=queue_name,
        task_name=task_name,
        requested_payload=_serialize_payload(requested_payload) or "{}",
        expires_at=expires_at,
    )
    session.add(job)
    session.flush()
    return _hydrate_job_payloads(job)


def get_async_job_by_id(
    session: Session,
    *,
    job_id: UUID,
) -> AsyncJob | None:
    job = session.get(AsyncJob, job_id)
    if job is None:
        return None
    return _hydrate_job_payloads(job)


def list_async_jobs_by_user(
    session: Session,
    *,
    requested_by_user_id: UUID,
    limit: int,
    offset: int = 0,
    job_type: AsyncJobType | None = None,
) -> tuple[list[AsyncJob], int]:
    priority = case(
        (AsyncJob.status == AsyncJobStatus.RUNNING, 0),
        (AsyncJob.status == AsyncJobStatus.QUEUED, 1),
        (AsyncJob.status == AsyncJobStatus.FAILED, 2),
        (AsyncJob.status == AsyncJobStatus.SUCCEEDED, 3),
        (AsyncJob.status == AsyncJobStatus.CANCELED, 4),
        else_=5,
    )
    conditions: list[ColumnElement[bool]] = [
        AsyncJob.requested_by_user_id == requested_by_user_id
    ]
    if job_type is not None:
        conditions.append(AsyncJob.job_type == job_type)

    items_stmt = (
        select(AsyncJob)
        .where(*conditions)
        .order_by(priority.asc(), AsyncJob.created_at.desc(), AsyncJob.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(items_stmt).all())
    for item in items:
        _hydrate_job_payloads(item)
    total_stmt = select(func.count(AsyncJob.id)).where(*conditions)
    total = int(session.execute(total_stmt).scalar_one())
    return items, total


def count_active_async_jobs(
    session: Session,
    *,
    job_type: AsyncJobType | None = None,
) -> int:
    conditions: list[ColumnElement[bool]] = [
        AsyncJob.status.in_([AsyncJobStatus.QUEUED, AsyncJobStatus.RUNNING])
    ]
    if job_type is not None:
        conditions.append(AsyncJob.job_type == job_type)
    stmt = select(func.count(AsyncJob.id)).where(*conditions)
    return int(session.execute(stmt).scalar_one())


def count_active_async_jobs_by_user(
    session: Session,
    *,
    requested_by_user_id: UUID,
    job_type: AsyncJobType | None = None,
) -> int:
    conditions: list[ColumnElement[bool]] = [
        AsyncJob.requested_by_user_id == requested_by_user_id,
        AsyncJob.status.in_([AsyncJobStatus.QUEUED, AsyncJobStatus.RUNNING]),
    ]
    if job_type is not None:
        conditions.append(AsyncJob.job_type == job_type)
    stmt = select(func.count(AsyncJob.id)).where(*conditions)
    return int(session.execute(stmt).scalar_one())


def update_async_job_status(
    session: Session,
    *,
    job: AsyncJob,
    status: AsyncJobStatus,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    result_payload: dict[str, object] | None = None,
    error_message: str | None = None,
    retry_count: int | None = None,
) -> AsyncJob:
    _prepare_job_payloads_for_flush(job)
    job.status = status
    if started_at is not None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    if result_payload is not None:
        job.result_payload = _serialize_payload(result_payload)
    if error_message is not None:
        job.error_message = error_message
    if retry_count is not None:
        job.retry_count = retry_count

    session.flush()
    return _hydrate_job_payloads(job)


def claim_queued_job_for_run(
    session: Session,
    *,
    job_id: UUID,
    started_at: datetime,
) -> AsyncJob | None:
    job = session.get(AsyncJob, job_id)
    if job is None or job.status != AsyncJobStatus.QUEUED:
        return None
    _prepare_job_payloads_for_flush(job)
    job.status = AsyncJobStatus.RUNNING
    job.started_at = started_at
    session.flush()
    return _hydrate_job_payloads(job)


def mark_async_jobs_expired_by_ids(
    session: Session,
    *,
    job_ids: list[UUID],
    expired_at: datetime,
) -> int:
    if not job_ids:
        return 0

    affected = 0
    for job_id in job_ids:
        job = session.get(AsyncJob, job_id)
        if job is None:
            continue
        if job.status == AsyncJobStatus.EXPIRED:
            continue
        _prepare_job_payloads_for_flush(job)
        job.status = AsyncJobStatus.EXPIRED
        job.finished_at = expired_at
        affected += 1
    if affected > 0:
        session.flush()
    return affected


def count_stale_running_async_jobs(
    session: Session,
    *,
    started_before: datetime,
) -> int:
    stmt = select(func.count(AsyncJob.id)).where(
        AsyncJob.status == AsyncJobStatus.RUNNING,
        AsyncJob.started_at.is_not(None),
        AsyncJob.started_at <= started_before,
    )
    return int(session.execute(stmt).scalar_one())


def list_stale_running_async_jobs(
    session: Session,
    *,
    started_before: datetime,
    limit: int,
    offset: int = 0,
) -> list[AsyncJob]:
    stmt = (
        select(AsyncJob)
        .where(
            AsyncJob.status == AsyncJobStatus.RUNNING,
            AsyncJob.started_at.is_not(None),
            AsyncJob.started_at <= started_before,
        )
        .order_by(AsyncJob.started_at.asc(), AsyncJob.id.asc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    for item in items:
        _hydrate_job_payloads(item)
    return items


def mark_async_jobs_failed_by_ids(
    session: Session,
    *,
    job_ids: list[UUID],
    failed_at: datetime,
    error_message: str,
) -> int:
    if not job_ids:
        return 0

    affected = 0
    for job_id in job_ids:
        job = session.get(AsyncJob, job_id)
        if job is None:
            continue
        if job.status != AsyncJobStatus.RUNNING:
            continue
        _prepare_job_payloads_for_flush(job)
        job.status = AsyncJobStatus.FAILED
        job.finished_at = failed_at
        job.error_message = error_message
        affected += 1
    if affected > 0:
        session.flush()
    return affected
