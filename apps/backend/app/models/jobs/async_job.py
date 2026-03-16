"""
汎用非同期ジョブテーブル定義.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class AsyncJobType(StrEnum):
    """非同期ジョブ種別."""

    AUTH_AUDIT_EXPORT = "auth_audit_export"
    SAMPLE_WAIT_BLOB = "sample_wait_blob"


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
            "ix_async_jobs_requested_by_user_id_status_job_type",
            "requested_by_user_id",
            "status",
            "job_type",
        ),
        Index(
            "ix_async_jobs_job_type_status_created_at",
            "job_type",
            "status",
            "created_at",
        ),
        Index("ix_async_jobs_expires_at", "expires_at"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.users.id", ondelete="NO ACTION"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AsyncJobStatus.QUEUED.value,
        server_default=text(f"'{AsyncJobStatus.QUEUED.value}'"),
    )
    queue_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_payload: Mapped[str] = mapped_column(
        NVARCHAR(length=None),
        nullable=False,
    )
    result_payload: Mapped[str | None] = mapped_column(
        NVARCHAR(length=None),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
        server_default=text("SYSUTCDATETIME()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
        server_default=text("SYSUTCDATETIME()"),
        onupdate=text("SYSUTCDATETIME()"),
    )
