"""AsyncJob リポジトリ."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select, update
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
    # 一覧画面では「いま動いているもの」を先に見せたいため、
    # created_at だけでなく status にも優先順位を持たせる。
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
    # API の投入制限では、まだ未処理の queued と実行中の running を
    # どちらも「枠を消費しているジョブ」として数える。
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
    # ユーザー単位の制限も global と同じく queued / running を対象にする。
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
    # 状態更新の共通窓口。呼び出し元が必要な項目だけを渡せるようにし、
    # 各 worker / API で更新ロジックを重複させない。
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


async def claim_queued_job_for_run(
    session: AsyncSession,
    *,
    job_id: UUID,
    started_at: datetime,
) -> AsyncJob | None:
    # queued のときだけ running に進める条件付き update。
    # 複数 worker が同じ job_id を同時に拾っても、最初の 1 件だけが claim できる。
    result = await session.execute(
        update(AsyncJob)
        .where(
            AsyncJob.id == job_id,
            AsyncJob.status == AsyncJobStatus.QUEUED,
        )
        .values(
            status=AsyncJobStatus.RUNNING,
            started_at=started_at,
        )
        .returning(AsyncJob)
    )
    claimed_job = result.scalar_one_or_none()
    if claimed_job is None:
        return None
    await session.flush()
    return claimed_job


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
        # すでに expired 済みのものは二重更新しない。
        if job.status == AsyncJobStatus.EXPIRED:
            continue
        job.status = AsyncJobStatus.EXPIRED
        job.finished_at = expired_at
        affected += 1
    if affected > 0:
        await session.flush()
    return affected


async def count_stale_running_async_jobs(
    session: AsyncSession,
    *,
    started_before: datetime,
) -> int:
    # cleanup では「started_at が入り、かつ一定時間を超えた running」を
    # stuck 候補として扱う。
    stmt = select(func.count(AsyncJob.id)).where(
        AsyncJob.status == AsyncJobStatus.RUNNING,
        AsyncJob.started_at.is_not(None),
        AsyncJob.started_at <= started_before,
    )
    return int((await session.execute(stmt)).scalar_one())


async def list_stale_running_async_jobs(
    session: AsyncSession,
    *,
    started_before: datetime,
    limit: int,
    offset: int = 0,
) -> list[AsyncJob]:
    # 長く詰まっているものから処理したいので started_at 昇順で返す。
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
    return list((await session.scalars(stmt)).all())


async def mark_async_jobs_failed_by_ids(
    session: AsyncSession,
    *,
    job_ids: list[UUID],
    failed_at: datetime,
    error_message: str,
) -> int:
    if not job_ids:
        return 0

    affected = 0
    for job_id in job_ids:
        job = await session.get(AsyncJob, job_id)
        if job is None:
            continue
        # cleanup では running のものだけを失敗化し、
        # 途中で別状態に変わったジョブは上書きしない。
        if job.status != AsyncJobStatus.RUNNING:
            continue
        job.status = AsyncJobStatus.FAILED
        job.finished_at = failed_at
        job.error_message = error_message
        affected += 1
    if affected > 0:
        await session.flush()
    return affected
