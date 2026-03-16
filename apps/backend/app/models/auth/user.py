"""
ユーザー本体テーブル定義.

- ユーザーの基本プロフィールを保持する
- 認証方式依存の情報は auth_identities 側へ分離する
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Index, String, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class UserType(StrEnum):
    """ユーザー種別."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class User(Base):
    """認証方式に依存しないユーザー本体情報."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_is_active", "is_active"),
        {"schema": "auth"},
    )

    id: Mapped[UUID] = mapped_column(UNIQUEIDENTIFIER, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_normalized: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str | None] = mapped_column(
        NVARCHAR(255),
        nullable=True,
    )
    user_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default=text("1"),
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
