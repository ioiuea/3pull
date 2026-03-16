"""
非同期ジョブ成果物テーブル定義.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.mssql import DATETIME2, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class AsyncJobArtifactType(StrEnum):
    """成果物種別."""

    AUTH_AUDIT_EXPORT_FILE = "auth_audit_export_file"
    SAMPLE_WAIT_BLOB_FILE = "sample_wait_blob_file"


class AsyncJobArtifact(Base):
    """非同期ジョブ成果物."""

    __tablename__ = "async_job_artifacts"
    __table_args__ = (
        Index("ix_async_job_artifacts_job_id_created_at", "job_id", "created_at"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
    )
    job_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("core.async_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    storage_provider: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="azure_blob",
        server_default=text("'azure_blob'"),
    )
    container_name: Mapped[str] = mapped_column(String(128), nullable=False)
    blob_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
        server_default=text("SYSUTCDATETIME()"),
    )
