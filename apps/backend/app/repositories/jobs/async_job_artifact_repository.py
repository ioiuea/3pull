"""AsyncJobArtifact リポジトリ."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs.async_job_artifact import AsyncJobArtifact, AsyncJobArtifactType


async def create_async_job_artifact(
    session: AsyncSession,
    *,
    job_id: UUID,
    artifact_type: AsyncJobArtifactType,
    container_name: str,
    blob_path: str,
    content_type: str,
    file_size_bytes: int,
    storage_provider: str = "azure_blob",
    checksum: str | None = None,
    expires_at: datetime | None = None,
) -> AsyncJobArtifact:
    # 成果物本体は Blob にあり、DB には参照用メタデータだけを保存する。
    artifact = AsyncJobArtifact(
        job_id=job_id,
        artifact_type=artifact_type,
        storage_provider=storage_provider,
        container_name=container_name,
        blob_path=blob_path,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
        checksum=checksum,
        expires_at=expires_at,
    )
    session.add(artifact)
    await session.flush()
    return artifact


async def get_latest_async_job_artifact(
    session: AsyncSession,
    *,
    job_id: UUID,
    artifact_type: AsyncJobArtifactType | None = None,
) -> AsyncJobArtifact | None:
    # ダウンロードや結果表示では「最新の 1 件」だけ見たいことが多いので、
    # created_at の降順で先頭を返す。
    stmt = select(AsyncJobArtifact).where(AsyncJobArtifact.job_id == job_id)
    if artifact_type is not None:
        stmt = stmt.where(AsyncJobArtifact.artifact_type == artifact_type)
    stmt = stmt.order_by(
        AsyncJobArtifact.created_at.desc(), AsyncJobArtifact.id.desc()
    ).limit(1)
    return (await session.scalars(stmt)).first()


async def get_async_job_artifact_by_id(
    session: AsyncSession,
    *,
    artifact_id: UUID,
) -> AsyncJobArtifact | None:
    return await session.get(AsyncJobArtifact, artifact_id)


async def list_async_job_artifacts_by_job(
    session: AsyncSession,
    *,
    job_id: UUID,
) -> list[AsyncJobArtifact]:
    # 一覧や詳細では新しい成果物から見たいので降順で返す。
    stmt = (
        select(AsyncJobArtifact)
        .where(AsyncJobArtifact.job_id == job_id)
        .order_by(AsyncJobArtifact.created_at.desc(), AsyncJobArtifact.id.desc())
    )
    return list((await session.scalars(stmt)).all())


async def count_expired_async_job_artifacts(
    session: AsyncSession,
    *,
    expires_before: datetime,
) -> int:
    stmt = select(func.count(AsyncJobArtifact.id)).where(
        AsyncJobArtifact.expires_at.is_not(None),
        AsyncJobArtifact.expires_at < expires_before,
    )
    return int((await session.execute(stmt)).scalar_one())


async def list_expired_async_job_artifacts(
    session: AsyncSession,
    *,
    expires_before: datetime,
    limit: int,
    offset: int = 0,
) -> list[AsyncJobArtifact]:
    # cleanup は古い期限切れから順に処理したいので expires_at 昇順で返す。
    stmt = (
        select(AsyncJobArtifact)
        .where(
            AsyncJobArtifact.expires_at.is_not(None),
            AsyncJobArtifact.expires_at < expires_before,
        )
        .order_by(AsyncJobArtifact.expires_at.asc(), AsyncJobArtifact.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.scalars(stmt)).all())


async def delete_async_job_artifacts_by_ids(
    session: AsyncSession,
    *,
    artifact_ids: list[UUID],
) -> int:
    if not artifact_ids:
        return 0
    # Blob 削除後に DB メタデータをまとめて消すため、ID の配列をそのまま受ける。
    stmt = delete(AsyncJobArtifact).where(AsyncJobArtifact.id.in_(artifact_ids))
    result = cast(CursorResult[object], await session.execute(stmt))
    return int(result.rowcount or 0)


async def count_async_job_artifacts_by_job_id(
    session: AsyncSession,
    *,
    job_id: UUID,
) -> int:
    stmt = select(func.count(AsyncJobArtifact.id)).where(
        AsyncJobArtifact.job_id == job_id
    )
    return int((await session.execute(stmt)).scalar_one())
