"""サンプル待機ジョブ作成エンドポイント."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session
from app.api.schemas.jobs import AsyncJobResponse
from app.core.settings import get_settings
from app.models.jobs.async_job import AsyncJobType
from app.repositories.jobs import (
    count_active_async_jobs,
    count_active_async_jobs_by_user,
    create_async_job,
)
from app.services.jobs import dispatch_async_job

from .common import require_session_user, router, to_job_response


class SampleWaitBlobCreateRequest(BaseModel):
    """サンプル待機ジョブ作成要求."""

    wait_seconds: int = Field(default=120, ge=1, le=600)
    content: str | None = Field(default=None, max_length=2048)
    retention_days: int | None = Field(default=None, ge=1)


@router.post(
    "/sample-wait-blob",
    response_model=AsyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_sample_wait_blob_job(
    request: Request,
    payload: SampleWaitBlobCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobResponse:
    """120秒待機 + Blob 保存を行うサンプルジョブを作成して enqueue する."""
    settings = get_settings()
    if not settings.celery_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "jobs_feature_disabled",
                "message": "Jobs feature is disabled",
            },
        )

    user = await require_session_user(request, session)

    global_active = await count_active_async_jobs(session)
    if global_active >= settings.celery_global_concurrency:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "jobs_global_concurrency_exceeded",
                "message": "Too many jobs are currently running",
            },
        )

    user_active = await count_active_async_jobs_by_user(
        session,
        requested_by_user_id=user.id,
    )
    if user_active >= settings.celery_per_user_concurrency:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "jobs_user_concurrency_exceeded",
                "message": "You already have a running job",
            },
        )

    queue_name = settings.sample_wait_blob_queue_name
    task_name = settings.sample_wait_blob_task_name
    requested_payload: dict[str, object] = {
        "wait_seconds": payload.wait_seconds,
        "content": payload.content,
    }
    retention_days = payload.retention_days or settings.celery_default_retention_days
    retention_days = min(retention_days, settings.celery_retention_max_days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

    job = await create_async_job(
        session,
        job_type=AsyncJobType.SAMPLE_WAIT_BLOB,
        requested_by_user_id=user.id,
        queue_name=queue_name,
        task_name=task_name,
        requested_payload=requested_payload,
        expires_at=expires_at,
    )

    try:
        dispatch_async_job(
            task_name=task_name,
            queue_name=queue_name,
            kwargs={"job_id": str(job.id)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "jobs_enqueue_failed", "message": "Failed to enqueue job"},
        ) from exc

    return to_job_response(job, artifacts=[])
