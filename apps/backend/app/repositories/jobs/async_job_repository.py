"""AsyncJob リポジトリ."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.jobs.async_job import AsyncJob, AsyncJobStatus, AsyncJobType


async def create_async_job(
    session: AsyncSession,
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
        requested_payload=requested_payload,
        expires_at=expires_at,
    )
    session.add(job)
    await session.flush()
    return job


async def get_async_job_by_id(
    session: AsyncSession,
    *,
    job_id: UUID,
) -> AsyncJob | None:
    return await session.get(AsyncJob, job_id)


async def list_async_jobs_by_user(
    session: AsyncSession,
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
    items = list((await session.scalars(items_stmt)).all())
    total_stmt = select(func.count(AsyncJob.id)).where(*conditions)
    total = int((await session.execute(total_stmt)).scalar_one())
    return items, total


async def count_active_async_jobs(
    session: AsyncSession,
    *,
    job_type: AsyncJobType | None = None,
) -> int:
    conditions: list[ColumnElement[bool]] = [
        AsyncJob.status.in_([AsyncJobStatus.QUEUED, AsyncJobStatus.RUNNING])
    ]
    if job_type is not None:
        conditions.append(AsyncJob.job_type == job_type)
    stmt = select(func.count(AsyncJob.id)).where(*conditions)
    return int((await session.execute(stmt)).scalar_one())


async def count_active_async_jobs_by_user(
    session: AsyncSession,
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
    return int((await session.execute(stmt)).scalar_one())


async def update_async_job_status(
    session: AsyncSession,
    *,
    job: AsyncJob,
    status: AsyncJobStatus,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    result_payload: dict[str, object] | None = None,
    error_message: str | None = None,
    retry_count: int | None = None,
) -> AsyncJob:
    job.status = status
    if started_at is not None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    if result_payload is not None:
        job.result_payload = result_payload
    if error_message is not None:
        job.error_message = error_message
    if retry_count is not None:
        job.retry_count = retry_count

    await session.flush()
    return job


async def mark_async_jobs_expired_by_ids(
    session: AsyncSession,
    *,
    job_ids: list[UUID],
    expired_at: datetime,
) -> int:
    if not job_ids:
        return 0

    affected = 0
    for job_id in job_ids:
        job = await session.get(AsyncJob, job_id)
        if job is None:
            continue
        if job.status == AsyncJobStatus.EXPIRED:
            continue
        job.status = AsyncJobStatus.EXPIRED
        job.finished_at = expired_at
        affected += 1
    if affected > 0:
        await session.flush()
    return affected
