"""ジョブ API 共通ヘルパー."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session
from app.adapters.storage import download_blob_bytes
from app.api.schemas.jobs import AsyncJobArtifactResponse, AsyncJobResponse
from app.core.settings import get_settings
from app.models.auth.user import User
from app.models.jobs.async_job import AsyncJob, AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifact, AsyncJobArtifactType
from app.repositories.jobs import (
    count_active_async_jobs,
    count_active_async_jobs_by_user,
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


def ensure_async_jobs_enabled() -> None:
    """非同期ジョブ機能が有効かを確認する."""
    # feature flag が無効な環境では、存在しない機能として 404 を返す。
    # これにより「未公開機能」をクライアントから見えにくくできる。
    if get_settings().async_jobs_enabled:
        return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "jobs_feature_disabled",
            "message": "Jobs feature is disabled",
        },
    )


async def enforce_async_job_concurrency(
    *,
    session: Session,
    requested_by_user_id: UUID,
    job_type: AsyncJobType,
) -> None:
    """指定 job_type の全体 / ユーザー単位の同時実行上限を確認する."""
    settings = get_settings()
    # 受付上限は job_type ごとに分ける。
    # こうしておくと、軽いサンプルジョブが重い export ジョブの枠を食い潰さない。
    global_active = count_active_async_jobs(session, job_type=job_type)
    if global_active >= settings.async_job_global_concurrency:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "jobs_global_concurrency_exceeded",
                "message": "Too many jobs of this type are currently running",
            },
        )

    user_active = count_active_async_jobs_by_user(
        session,
        requested_by_user_id=requested_by_user_id,
        job_type=job_type,
    )
    if user_active >= settings.async_job_per_user_concurrency:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "jobs_user_concurrency_exceeded",
                "message": "You already have a running job of this type",
            },
        )


def resolve_async_job_expiration(
    *,
    retention_days: int | None,
) -> datetime:
    """保持日数を設定値で補正し、期限日時を返す."""
    settings = get_settings()
    # API から任意の日数が来ても、最終的にはサーバー側の上限で丸める。
    # これにより、極端に長い保持をリクエストされても運用ポリシーを守れる。
    effective_retention_days = (
        retention_days or settings.async_job_default_retention_days
    )
    effective_retention_days = min(
        effective_retention_days,
        settings.async_job_retention_max_days,
    )
    return datetime.now(timezone.utc) + timedelta(days=effective_retention_days)


def raise_session_error(error: SessionAuthError) -> NoReturn:
    """セッション解決エラーを HTTP 例外へ変換する."""
    # 認証サービス側のドメインエラーを、API 用の HTTP 応答へ寄せる変換点。
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
    session: Session,
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
    # API 層では ORM モデルを直接返さず、外部公開用のスキーマへ明示変換する。
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
    # requested_payload / result_payload は JSON カラムなので、レスポンス化前に
    # dict へ明示変換しておくと、シリアライズ時の扱いが安定する。
    return AsyncJobResponse(
        id=job.id,
        job_type=AsyncJobType(job.job_type),
        requested_by_user_id=job.requested_by_user_id,
        status=AsyncJobStatus(job.status),
        requested_payload=job.requested_payload
        if isinstance(job.requested_payload, dict)
        else {},
        result_payload=job.result_payload
        if isinstance(job.result_payload, dict)
        else None,
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
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """成果物を backend 経由でダウンロードする."""
    # Blob の直接 URL を返さず backend 経由にすることで、
    # 認可は常に「このユーザーの成果物か」で統一できる。
    user = await require_session_user(request, session)
    job = get_async_job_by_id(session, job_id=job_id)
    if job is None or job.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )
    artifact = get_async_job_artifact_by_id(session, artifact_id=artifact_id)
    if artifact is None or artifact.job_id != job.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "artifact_not_found", "message": "Artifact not found"},
        )

    data = download_blob_bytes(blob_path=artifact.blob_path)
    # まず全件メモリに載せるシンプル実装。現状の成果物サイズ前提ではこれで十分。
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
    session: Session,
    job_id: UUID,
) -> tuple[AsyncJob, list[AsyncJobArtifact]]:
    """ジョブの所有者チェックを行って詳細を返す."""
    # 参照系 API で毎回同じ所有者確認をするため、共通化して重複を減らす。
    user = await require_session_user(request, session)
    job = get_async_job_by_id(session, job_id=job_id)
    if job is None or job.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )
    artifacts = list_async_job_artifacts_by_job(session, job_id=job.id)
    return job, artifacts
