"""汎用ジョブ API スキーマ."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.jobs.async_job import AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifactType


class AsyncJobCreateRequest(BaseModel):
    """ジョブ作成要求."""

    job_type: AsyncJobType
    payload: dict[str, object] = Field(default_factory=dict)
    retention_days: int | None = Field(default=None, ge=1)


class AsyncJobArtifactResponse(BaseModel):
    """ジョブ成果物."""

    id: UUID
    artifact_type: AsyncJobArtifactType
    storage_provider: str
    container_name: str
    blob_path: str
    content_type: str
    file_size_bytes: int
    checksum: str | None
    expires_at: datetime | None
    created_at: datetime


class AsyncJobResponse(BaseModel):
    """ジョブ応答."""

    id: UUID
    job_type: AsyncJobType
    requested_by_user_id: UUID | None
    status: AsyncJobStatus
    requested_payload: dict[str, object]
    result_payload: dict[str, object] | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    finished_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    artifacts: list[AsyncJobArtifactResponse]


class AsyncJobListResponse(BaseModel):
    """ジョブ一覧応答."""

    total: int
    items: list[AsyncJobResponse]
