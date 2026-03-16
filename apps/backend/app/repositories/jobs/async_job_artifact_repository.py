"""AsyncJobArtifact リポジトリ."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.jobs.async_job_artifact import AsyncJobArtifact, AsyncJobArtifactType


def create_async_job_artifact(
    session: Session,
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
    session.flush()
    return artifact


def get_latest_async_job_artifact(
    session: Session,
    *,
    job_id: UUID,
    artifact_type: AsyncJobArtifactType | None = None,
) -> AsyncJobArtifact | None:
    stmt = select(AsyncJobArtifact).where(AsyncJobArtifact.job_id == job_id)
    if artifact_type is not None:
        stmt = stmt.where(AsyncJobArtifact.artifact_type == artifact_type)
    stmt = stmt.order_by(
        AsyncJobArtifact.created_at.desc(), AsyncJobArtifact.id.desc()
    ).limit(1)
    return session.scalars(stmt).first()


def get_async_job_artifact_by_id(
    session: Session,
    *,
    artifact_id: UUID,
) -> AsyncJobArtifact | None:
    return session.get(AsyncJobArtifact, artifact_id)


def list_async_job_artifacts_by_job(
    session: Session,
    *,
    job_id: UUID,
) -> list[AsyncJobArtifact]:
    stmt = (
        select(AsyncJobArtifact)
        .where(AsyncJobArtifact.job_id == job_id)
        .order_by(AsyncJobArtifact.created_at.desc(), AsyncJobArtifact.id.desc())
    )
    return list(session.scalars(stmt).all())


def count_expired_async_job_artifacts(
    session: Session,
    *,
    expires_before: datetime,
) -> int:
    stmt = select(func.count(AsyncJobArtifact.id)).where(
        AsyncJobArtifact.expires_at.is_not(None),
        AsyncJobArtifact.expires_at < expires_before,
    )
    return int(session.execute(stmt).scalar_one())


def list_expired_async_job_artifacts(
    session: Session,
    *,
    expires_before: datetime,
    limit: int,
    offset: int = 0,
) -> list[AsyncJobArtifact]:
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
    return list(session.scalars(stmt).all())


def delete_async_job_artifacts_by_ids(
    session: Session,
    *,
    artifact_ids: list[UUID],
) -> int:
    if not artifact_ids:
        return 0
    stmt = delete(AsyncJobArtifact).where(AsyncJobArtifact.id.in_(artifact_ids))
    session.execute(stmt)
    return len(artifact_ids)


def count_async_job_artifacts_by_job_id(
    session: Session,
    *,
    job_id: UUID,
) -> int:
    stmt = select(func.count(AsyncJobArtifact.id)).where(
        AsyncJobArtifact.job_id == job_id
    )
    return int(session.execute(stmt).scalar_one())
