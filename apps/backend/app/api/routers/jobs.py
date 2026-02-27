"""汎用ジョブ API ルーター."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session
from app.adapters.storage import download_blob_bytes
from app.api.schemas.jobs import (
    AsyncJobArtifactResponse,
    AsyncJobCreateRequest,
    AsyncJobListResponse,
    AsyncJobResponse,
)
from app.core.settings import get_settings
from app.models.auth.auth_audit_log import AuthAuditEventType
from app.models.auth.user import User
from app.models.jobs.async_job import AsyncJob, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifact
from app.repositories.jobs import (
    count_active_async_jobs,
    count_active_async_jobs_by_user,
    create_async_job,
    get_async_job_artifact_by_id,
    get_async_job_by_id,
    list_async_job_artifacts_by_job,
    list_async_jobs_by_user,
)
from app.services.auth.session_auth_service import (
    SessionAuthError,
    SessionAuthErrorCode,
    resolve_user_by_session_token,
)
from app.services.jobs import dispatch_async_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


class _AuthAuditExportPayload(BaseModel):
    event_type: AuthAuditEventType | None = None
    provider: str | None = None
    keyword: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    timezone: str = Field(default="UTC")


def _raise_session_error(error: SessionAuthError) -> NoReturn:
    status_code_map: dict[SessionAuthErrorCode, int] = {
        SessionAuthErrorCode.SESSION_INVALID: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.SESSION_EXPIRED: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.USER_NOT_FOUND: status.HTTP_401_UNAUTHORIZED,
    }
    raise HTTPException(
        status_code=status_code_map.get(error.code, status.HTTP_401_UNAUTHORIZED),
        detail={"code": error.code.value, "message": error.message},
    )


async def _require_session_user(
    request: Request,
    session: AsyncSession,
) -> User:
    cookie_name = get_settings().session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_missing", "message": "Session cookie is missing"},
        )
    try:
        return await resolve_user_by_session_token(session, raw_token=raw_token)
    except SessionAuthError as error:
        _raise_session_error(error)


def _to_artifact_response(artifact: AsyncJobArtifact) -> AsyncJobArtifactResponse:
    return AsyncJobArtifactResponse(
        id=artifact.id,
        artifact_type=artifact.artifact_type,
        storage_provider=artifact.storage_provider,
        container_name=artifact.container_name,
        blob_path=artifact.blob_path,
        content_type=artifact.content_type,
        file_size_bytes=artifact.file_size_bytes,
        checksum=artifact.checksum,
        expires_at=artifact.expires_at,
        created_at=artifact.created_at,
    )


def _to_job_response(
    job: AsyncJob,
    *,
    artifacts: list[AsyncJobArtifact],
) -> AsyncJobResponse:
    return AsyncJobResponse(
        id=job.id,
        job_type=job.job_type,
        requested_by_user_id=job.requested_by_user_id,
        status=job.status,
        requested_payload=dict(job.requested_payload),
        result_payload=dict(job.result_payload)
        if job.result_payload is not None
        else None,
        error_message=job.error_message,
        retry_count=job.retry_count,
        started_at=job.started_at,
        finished_at=job.finished_at,
        expires_at=job.expires_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        artifacts=[_to_artifact_response(item) for item in artifacts],
    )


def _resolve_task_binding(job_type: AsyncJobType) -> tuple[str, str]:
    settings = get_settings()
    if job_type == AsyncJobType.AUTH_AUDIT_EXPORT:
        return (
            settings.auth_audit_export_queue_name,
            settings.auth_audit_export_task_name,
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "unsupported_job_type", "message": "Unsupported job_type"},
    )


def _normalize_requested_payload(
    *,
    job_type: AsyncJobType,
    payload: dict[str, object],
) -> dict[str, object]:
    if job_type == AsyncJobType.AUTH_AUDIT_EXPORT:
        normalized = _AuthAuditExportPayload.model_validate(payload)
        return {
            "requested_filters": {
                "event_type": normalized.event_type.value
                if normalized.event_type
                else None,
                "provider": normalized.provider,
                "keyword": normalized.keyword,
                "date_from": normalized.date_from.isoformat()
                if normalized.date_from
                else None,
                "date_to": normalized.date_to.isoformat()
                if normalized.date_to
                else None,
            },
            "timezone": normalized.timezone,
        }
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "unsupported_job_type", "message": "Unsupported job_type"},
    )


@router.post("", response_model=AsyncJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: Request,
    payload: AsyncJobCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobResponse:
    settings = get_settings()
    if not settings.celery_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "jobs_feature_disabled",
                "message": "Jobs feature is disabled",
            },
        )

    user = await _require_session_user(request, session)

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

    queue_name, task_name = _resolve_task_binding(payload.job_type)
    requested_payload = _normalize_requested_payload(
        job_type=payload.job_type,
        payload=payload.payload,
    )
    retention_days = payload.retention_days or settings.celery_default_retention_days
    retention_days = min(retention_days, settings.celery_retention_max_days)
    expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

    job = await create_async_job(
        session,
        job_type=payload.job_type,
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

    return _to_job_response(job, artifacts=[])


@router.get("", response_model=AsyncJobListResponse)
async def list_jobs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    job_type: AsyncJobType | None = None,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobListResponse:
    user = await _require_session_user(request, session)
    items, total = await list_async_jobs_by_user(
        session,
        requested_by_user_id=user.id,
        limit=page_size,
        offset=(page - 1) * page_size,
        job_type=job_type,
    )
    artifacts_map: dict[UUID, list[AsyncJobArtifact]] = {}
    for item in items:
        artifacts_map[item.id] = await list_async_job_artifacts_by_job(
            session, job_id=item.id
        )
    return AsyncJobListResponse(
        total=total,
        items=[
            _to_job_response(item, artifacts=artifacts_map[item.id]) for item in items
        ],
    )


@router.get("/{job_id}", response_model=AsyncJobResponse)
async def get_job(
    request: Request,
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobResponse:
    user = await _require_session_user(request, session)
    job = await get_async_job_by_id(session, job_id=job_id)
    if job is None or job.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )
    artifacts = await list_async_job_artifacts_by_job(session, job_id=job.id)
    return _to_job_response(job, artifacts=artifacts)


@router.get("/{job_id}/artifacts/{artifact_id}/download")
async def download_job_artifact(
    request: Request,
    job_id: UUID,
    artifact_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    user = await _require_session_user(request, session)
    job = await get_async_job_by_id(session, job_id=job_id)
    if job is None or job.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )
    artifact = await get_async_job_artifact_by_id(session, artifact_id=artifact_id)
    if artifact is None or artifact.job_id != job.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "artifact_not_found", "message": "Artifact not found"},
        )

    data = download_blob_bytes(blob_path=artifact.blob_path)
    return StreamingResponse(
        BytesIO(data),
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": (f'attachment; filename="{artifact.id}"'),
        },
    )
