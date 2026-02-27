"""
汎用非同期ジョブテーブル定義.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgres.base import Base


class AsyncJobType(StrEnum):
    """非同期ジョブ種別."""

    AUTH_AUDIT_EXPORT = "auth_audit_export"


class AsyncJobStatus(StrEnum):
    """非同期ジョブ状態."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"


class AsyncJob(Base):
    """汎用非同期ジョブ."""

    __tablename__ = "async_jobs"
    __table_args__ = (
        Index(
            "ix_async_jobs_requested_by_user_id_created_at",
            "requested_by_user_id",
            "created_at",
        ),
        Index(
            "ix_async_jobs_job_type_status_created_at",
            "job_type",
            "status",
            "created_at",
        ),
        Index("ix_async_jobs_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    job_type: Mapped[AsyncJobType] = mapped_column(
        Enum(
            AsyncJobType,
            name="async_job_type",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[AsyncJobStatus] = mapped_column(
        Enum(
            AsyncJobStatus,
            name="async_job_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AsyncJobStatus.QUEUED,
        server_default=AsyncJobStatus.QUEUED.value,
    )
    queue_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    result_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
