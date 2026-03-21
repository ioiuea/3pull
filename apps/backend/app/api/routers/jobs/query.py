"""ジョブ参照系エンドポイント."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session
from app.api.schemas.jobs import AsyncJobListResponse, AsyncJobResponse
from app.core.security.http import CurrentUserDep
from app.models.jobs.async_job import AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifact
from app.repositories.jobs import (
    list_async_job_artifacts_by_job,
    list_async_jobs_by_user,
)

from .helpers import get_owned_job_with_artifacts, router, to_job_response


@router.get("", response_model=AsyncJobListResponse)
async def list_jobs(
    user: CurrentUserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    job_type: AsyncJobType | None = None,
    session: Session = Depends(get_session),
) -> AsyncJobListResponse:
    """自分のジョブ一覧を返す."""
    # 一覧取得でも必ず本人のジョブだけに絞る。管理者一覧 API は別で作る前提。
    items, total = list_async_jobs_by_user(
        session,
        requested_by_user_id=user.id,
        limit=page_size,
        offset=(page - 1) * page_size,
        job_type=job_type,
    )
    artifacts_map: dict[UUID, list[AsyncJobArtifact]] = {}
    for item in items:
        # 現状はシンプルさ優先で、各 job ごとに成果物を読み出す。
        # 件数が増えて問題になったら join / batch 化を検討する。
        artifacts_map[item.id] = list_async_job_artifacts_by_job(
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
    user: CurrentUserDep,
    job_id: UUID,
    session: Session = Depends(get_session),
) -> AsyncJobResponse:
    """自分のジョブ詳細を返す."""
    target, artifacts = get_owned_job_with_artifacts(
        session=session,
        job_id=job_id,
        requested_by_user_id=user.id,
    )
    return to_job_response(target, artifacts=artifacts)
