"""サンプル待機ジョブ作成エンドポイント."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session, get_session_factory
from app.api.schemas.jobs import AsyncJobResponse
from app.core.security.session import require_session_user
from app.core.settings import get_settings
from app.models.jobs.async_job import AsyncJobType
from app.repositories.jobs import create_async_job
from app.services.jobs import dispatch_async_job

from ..helpers import (
    enforce_async_job_concurrency,
    ensure_async_jobs_enabled,
    resolve_async_job_expiration,
    router,
    to_job_response,
)


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
    session: Session = Depends(get_session),
) -> AsyncJobResponse:
    """120秒待機 + Blob 保存を行うサンプルジョブを作成して enqueue する."""
    settings = get_settings()
    ensure_async_jobs_enabled()

    # サンプルジョブも本番ジョブと同じ入口を通し、認証・上限チェックの挙動を揃える。
    user = await require_session_user(request, session)
    await enforce_async_job_concurrency(
        session=session,
        requested_by_user_id=user.id,
        job_type=AsyncJobType.SAMPLE_WAIT_BLOB,
    )

    queue_name = settings.sample_wait_blob_queue_name
    task_name = settings.sample_wait_blob_task_name
    requested_payload: dict[str, object] = {
        # worker は requested_payload を見て待機秒数や書き込む内容を決める。
        "wait_seconds": payload.wait_seconds,
        "content": payload.content,
    }
    expires_at = resolve_async_job_expiration(retention_days=payload.retention_days)

    session_factory = get_session_factory()
    # 先にジョブ行をコミットしてから enqueue し、worker から確実に参照できる状態にする。
    with session_factory.begin() as write_session:
        job = create_async_job(
            write_session,
            job_type=AsyncJobType.SAMPLE_WAIT_BLOB,
            requested_by_user_id=user.id,
            queue_name=queue_name,
            task_name=task_name,
            requested_payload=requested_payload,
            expires_at=expires_at,
        )

    try:
        # メッセージ本文は最小限にし、DB 上の job レコードを処理の正本とする。
        dispatch_async_job(
            task_name=task_name,
            queue_name=queue_name,
            kwargs={"job_id": str(job.id)},
        )
    except Exception as exc:
        # Service Bus 側の一時障害は 503 で返し、クライアントに再試行判断を委ねる。
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "jobs_enqueue_failed", "message": "Failed to enqueue job"},
        ) from exc

    return to_job_response(job, artifacts=[])
