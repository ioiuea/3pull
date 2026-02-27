"""ジョブ参照系エンドポイント."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.session import get_session
from app.api.schemas.jobs import AsyncJobListResponse, AsyncJobResponse
from app.models.jobs.async_job import AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifact
from app.repositories.jobs import (
    get_async_job_by_id,
    list_async_job_artifacts_by_job,
    list_async_jobs_by_user,
)

from .common import require_session_user, router, to_job_response


@router.get("", response_model=AsyncJobListResponse)
async def list_jobs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    job_type: AsyncJobType | None = None,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobListResponse:
    """自分のジョブ一覧を返す."""
    user = await require_session_user(request, session)
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
            session,
            job_id=item.id,
        )
    return AsyncJobListResponse(
        total=total,
        items=[
            to_job_response(item, artifacts=artifacts_map[item.id]) for item in items
        ],
    )


@router.get("/{job_id}", response_model=AsyncJobResponse)
async def get_job(
    request: Request,
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AsyncJobResponse:
    """自分のジョブ詳細を返す."""
    user = await require_session_user(request, session)
    target = await get_async_job_by_id(session, job_id=job_id)
    if target is None or target.requested_by_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job not found"},
        )
    artifacts = await list_async_job_artifacts_by_job(session, job_id=target.id)
    return to_job_response(target, artifacts=artifacts)
