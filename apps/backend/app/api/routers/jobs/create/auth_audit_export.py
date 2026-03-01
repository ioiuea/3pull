"""監査ログエクスポートジョブ作成エンドポイント."""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session, get_session_factory
from app.api.schemas.jobs import AsyncJobResponse
from app.core.settings import get_settings
from app.models.auth.auth_audit_log import AuthAuditEventType
from app.models.jobs.async_job import AsyncJobType
from app.repositories.jobs import create_async_job
from app.services.jobs import dispatch_async_job

from ..helpers import (
    enforce_async_job_concurrency,
    ensure_async_jobs_enabled,
    require_session_user,
    resolve_async_job_expiration,
    router,
    to_job_response,
)


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
    ensure_async_jobs_enabled()

    # まず「誰のジョブか」を確定し、そのユーザー単位で投入可否を判定する。
    user = await require_session_user(request, session)
    await enforce_async_job_concurrency(
        session=session,
        requested_by_user_id=user.id,
        job_type=AsyncJobType.AUTH_AUDIT_EXPORT,
    )

    queue_name = settings.auth_audit_export_queue_name
    task_name = settings.auth_audit_export_task_name
    requested_payload: dict[str, object] = {
        # 監査ログ export の検索条件は、そのまま後で worker が参照できるよう
        # requested_payload に保存しておく。
        "requested_filters": {
            "event_type": payload.event_type.value if payload.event_type else None,
            "provider": payload.provider,
            "keyword": payload.keyword,
            "date_from": payload.date_from.isoformat() if payload.date_from else None,
            "date_to": payload.date_to.isoformat() if payload.date_to else None,
        },
        "timezone": payload.timezone,
    }
    expires_at = resolve_async_job_expiration(retention_days=payload.retention_days)

    session_factory = get_session_factory()
    # enqueue より先に DB へコミットしておかないと、worker が先にメッセージを拾った時に
    # 対象 job 行がまだ見えず、無駄な再試行が起きる。
    async with session_factory() as write_session:
        async with write_session.begin():
            job = await create_async_job(
                write_session,
                job_type=AsyncJobType.AUTH_AUDIT_EXPORT,
                requested_by_user_id=user.id,
                queue_name=queue_name,
                task_name=task_name,
                requested_payload=requested_payload,
                expires_at=expires_at,
            )

    try:
        # メッセージには job_id だけを載せ、詳細は DB を正本として worker が読む。
        dispatch_async_job(
            task_name=task_name,
            queue_name=queue_name,
            kwargs={"job_id": str(job.id)},
        )
    except Exception as exc:
        # DB 作成後に enqueue だけ失敗したケースは、呼び出し元には 503 として返す。
        # 残った queued job の扱いは cleanup / 運用側で追えるようにしている。
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "jobs_enqueue_failed", "message": "Failed to enqueue job"},
        ) from exc

    return to_job_response(job, artifacts=[])
