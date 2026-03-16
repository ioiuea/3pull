"""
認証アイデンティティテーブル定義.

- ユーザー 1 件に対して複数の認証手段（Entra / Email）を紐づける
- provider + provider_subject を外部 IdP の一意識別子として扱う
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.mssql import DATETIME2, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class AuthProvider(StrEnum):
    """認証プロバイダー種別."""

    ENTRA = "entra"
    EMAIL = "email"


class AuthIdentity(Base):
    """認証方式ごとの外部識別子・認証情報."""

    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_auth_identities_provider_subject",
        ),
        Index("ix_auth_identities_user_id", "user_id"),
        Index("ix_auth_identities_email_normalized", "email_normalized"),
        {"schema": "auth"},
    )

    id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_normalized: Mapped[str | None] = mapped_column(String(320), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
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
