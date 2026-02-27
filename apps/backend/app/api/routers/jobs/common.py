"""ジョブ API 共通ヘルパー."""

from __future__ import annotations

from io import BytesIO
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session
from app.adapters.storage import download_blob_bytes
from app.api.schemas.jobs import AsyncJobArtifactResponse, AsyncJobResponse
from app.core.settings import get_settings
from app.models.auth.user import User
from app.models.jobs.async_job import AsyncJob, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifact, AsyncJobArtifactType
from app.repositories.jobs import (
    get_async_job_artifact_by_id,
    get_async_job_by_id,
    list_async_job_artifacts_by_job,
)
from app.services.auth.session_auth_service import (
    SessionAuthError,
    SessionAuthErrorCode,
    resolve_user_by_session_token,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def raise_session_error(error: SessionAuthError) -> NoReturn:
    """セッション解決エラーを HTTP 例外へ変換する."""
    status_code_map: dict[SessionAuthErrorCode, int] = {
        SessionAuthErrorCode.SESSION_INVALID: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.SESSION_EXPIRED: status.HTTP_401_UNAUTHORIZED,
        SessionAuthErrorCode.USER_NOT_FOUND: status.HTTP_401_UNAUTHORIZED,
    }
    raise HTTPException(
        status_code=status_code_map.get(error.code, status.HTTP_401_UNAUTHORIZED),
        detail={"code": error.code.value, "message": error.message},
    )


async def require_session_user(
    request: Request,
    session: AsyncSession,
) -> User:
    """Cookie セッションからログインユーザーを解決する."""
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
        raise_session_error(error)


def to_artifact_response(artifact: AsyncJobArtifact) -> AsyncJobArtifactResponse:
    """DB モデルを API 応答スキーマへ変換する."""
    return AsyncJobArtifactResponse(
        id=artifact.id,
        artifact_type=AsyncJobArtifactType(artifact.artifact_type),
        storage_provider=artifact.storage_provider,
        container_name=artifact.container_name,
        blob_path=artifact.blob_path,
        content_type=artifact.content_type,
        file_size_bytes=artifact.file_size_bytes,
        checksum=artifact.checksum,
        expires_at=artifact.expires_at,
        created_at=artifact.created_at,
    )


def to_job_response(
    job: AsyncJob,
    *,
    artifacts: list[AsyncJobArtifact],
) -> AsyncJobResponse:
    """DB モデルを API 応答スキーマへ変換する."""
    return AsyncJobResponse(
        id=job.id,
        job_type=AsyncJobType(job.job_type),
        requested_by_user_id=job.requested_by_user_id,
        status=job.status,
        requested_payload=dict(job.requested_payload),
        result_payload=(
            dict(job.result_payload) if job.result_payload is not None else None
        ),
        error_message=job.error_message,
        retry_count=job.retry_count,
        started_at=job.started_at,
        finished_at=job.finished_at,
        expires_at=job.expires_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        artifacts=[to_artifact_response(item) for item in artifacts],
    )


@router.get("/{job_id}/artifacts/{artifact_id}/download")
async def download_job_artifact(
    request: Request,
    job_id: UUID,
    artifact_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """成果物を backend 経由でダウンロードする."""
    user = await require_session_user(request, session)
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


async def get_job_with_owner_check(
    *,
    request: Request,
    session: AsyncSession,
    job_id: UUID,
) -> tuple[AsyncJob, list[AsyncJobArtifact]]:
    """ジョブの所有者チェックを行って詳細を返す."""
    user = await require_session_user(request, session)
    job = await get_async_job_by_id(session, job_id=job_id)
    if job is None or job.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )
    artifacts = await list_async_job_artifacts_by_job(session, job_id=job.id)
    return job, artifacts
