"""ジョブ制御系エンドポイント."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session
from app.api.schemas.jobs import AsyncJobResponse
from app.models.jobs.async_job import AsyncJobStatus
from app.repositories.jobs import (
    get_async_job_by_id,
    list_async_job_artifacts_by_job,
    update_async_job_status,
)

from .helpers import require_session_user, router, to_job_response


@router.post("/{job_id}/cancel", response_model=AsyncJobResponse)
async def cancel_job(
    request: Request,
    job_id: UUID,
    session: Session = Depends(get_session),
) -> AsyncJobResponse:
    """自分の queued/running ジョブをキャンセルする."""
    user = await require_session_user(request, session)
    job = get_async_job_by_id(session, job_id=job_id)
    # 他人のジョブの存在を見せないため、未存在と他人所有は同じ 404 にする。
    if job is None or job.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )

    if job.status == AsyncJobStatus.CANCELED:
        # すでに canceled なら冪等に成功扱いで最新状態を返す。
        artifacts = list_async_job_artifacts_by_job(session, job_id=job.id)
        return to_job_response(job, artifacts=artifacts)

    if job.status in {
        AsyncJobStatus.SUCCEEDED,
        AsyncJobStatus.FAILED,
        AsyncJobStatus.EXPIRED,
    }:
        # 終了済みジョブは後から止められないので 409 を返す。
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "job_not_cancelable",
                "message": f"Job cannot be canceled in status: {job.status}",
            },
        )

    update_async_job_status(
        session,
        job=job,
        status=AsyncJobStatus.CANCELED,
        # Service Bus のメッセージ自体は残っていても、
        # worker 側がこの status を見て no-op にする。
        finished_at=datetime.now(timezone.utc),
        error_message=None,
    )
    # onupdate で更新される updated_at などの遅延ロードを避けるため、
    # レスポンス化前に最新値を明示取得する。
    session.refresh(job)
    artifacts = list_async_job_artifacts_by_job(session, job_id=job.id)
    return to_job_response(job, artifacts=artifacts)
