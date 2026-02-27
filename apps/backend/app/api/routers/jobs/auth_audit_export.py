"""監査ログエクスポートジョブ作成エンドポイント."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session
from app.api.schemas.jobs import AsyncJobResponse
from app.core.settings import get_settings
from app.models.auth.auth_audit_log import AuthAuditEventType
from app.models.jobs.async_job import AsyncJobType
from app.repositories.jobs import (
    count_active_async_jobs,
    count_active_async_jobs_by_user,
    create_async_job,
)
from app.services.jobs import dispatch_async_job

from .common import require_session_user, router, to_job_response


class AuthAuditExportCreateRequest(BaseModel):
    """監査ログエクスポート作成要求."""

    event_type: AuthAuditEventType | None = None
    provider: str | None = None
    keyword: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    timezone: str = Field(default="UTC")
    retention_days: int | None = Field(default=None, ge=1)


@router.post(
    "/auth-audit-export",
    response_model=AsyncJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_auth_audit_export_job(
    request: Request,
    payload: AuthAuditExportCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobResponse:
    """監査ログエクスポートジョブを作成して enqueue する."""
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

    queue_name = settings.auth_audit_export_queue_name
    task_name = settings.auth_audit_export_task_name
    requested_payload: dict[str, object] = {
        "requested_filters": {
            "event_type": payload.event_type.value if payload.event_type else None,
            "provider": payload.provider,
            "keyword": payload.keyword,
            "date_from": payload.date_from.isoformat() if payload.date_from else None,
            "date_to": payload.date_to.isoformat() if payload.date_to else None,
        },
        "timezone": payload.timezone,
    }
    retention_days = payload.retention_days or settings.celery_default_retention_days
    retention_days = min(retention_days, settings.celery_retention_max_days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

    job = await create_async_job(
        session,
        job_type=AsyncJobType.AUTH_AUDIT_EXPORT,
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
