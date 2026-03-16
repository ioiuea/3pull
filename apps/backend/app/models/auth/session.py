"""
アプリケーションセッションテーブル定義.

- ログイン後のセッション状態を保持する
- セッショントークンはハッシュ化して保存し、生値は保持しない
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class UserSession(Base):
    """アプリケーションのログインセッション."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_id_revoked_at", "user_id", "revoked_at"),
        Index("ix_sessions_expires_at", "expires_at"),
        {"schema": "auth"},
    )

    id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.users.id", ondelete="NO ACTION"),
        nullable=False,
    )
    auth_identity_id: Mapped[UUID | None] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.auth_identities.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    entra_access_token: Mapped[str | None] = mapped_column(
        NVARCHAR(length=None),
        nullable=True,
    )
    entra_refresh_token: Mapped[str | None] = mapped_column(
        NVARCHAR(length=None),
        nullable=True,
    )
    entra_access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
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
