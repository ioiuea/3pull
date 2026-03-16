"""
メール検証トークンテーブル定義.

- Email identity 向けのワンタイム検証トークンを管理する
- 生トークンは保存せずハッシュのみ保存する
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.mssql import DATETIME2, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class EmailVerificationToken(Base):
    """メール検証用のワンタイムトークン."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index(
            "ix_email_verification_tokens_identity_id_consumed_at",
            "identity_id",
            "consumed_at",
        ),
        {"schema": "auth"},
    )

    id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=uuid4,
    )
    identity_id: Mapped[UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.auth_identities.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DATETIME2(precision=3),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
        server_default=text("SYSUTCDATETIME()"),
    )
