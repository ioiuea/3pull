"""
認証監査ログテーブル定義.

- 認証関連イベントの監査証跡を保持する
- Azure SQL では通常テーブル + インデックス + retention cleanup で運用する
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.sql.base import Base


class AuthAuditEventType(StrEnum):
    """監査ログに保存する認証イベント種別."""

    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAIL = "auth.login.fail"
    LOGOUT_SUCCESS = "auth.logout.success"
    LOGOUT_FAIL = "auth.logout.fail"
    SESSION_REFRESH_SUCCESS = "auth.session_refresh.success"
    SESSION_REFRESH_FAIL = "auth.session_refresh.fail"
    SESSION_REVOKE_SUCCESS = "auth.session_revoke.success"
    SESSION_REVOKE_FAIL = "auth.session_revoke.fail"
    SIGNUP_SUCCESS = "auth.signup.success"
    SIGNUP_FAIL = "auth.signup.fail"
    EMAIL_VERIFY_SUCCESS = "auth.email_verify.success"
    EMAIL_VERIFY_FAIL = "auth.email_verify.fail"
    PASSWORD_CHANGE_SUCCESS = "auth.password_change.success"
    PASSWORD_CHANGE_FAIL = "auth.password_change.fail"
    PASSWORD_RESET_REQUEST_SUCCESS = "auth.password_reset_request.success"
    PASSWORD_RESET_REQUEST_FAIL = "auth.password_reset_request.fail"
    PASSWORD_RESET_CONFIRM_SUCCESS = "auth.password_reset_confirm.success"
    PASSWORD_RESET_CONFIRM_FAIL = "auth.password_reset_confirm.fail"
    ENTRA_CALLBACK_SUCCESS = "auth.entra_callback.success"
    ENTRA_CALLBACK_FAIL = "auth.entra_callback.fail"
    ENTRA_PROFILE_FETCH_SUCCESS = "auth.entra_profile_fetch.success"
    ENTRA_PROFILE_FETCH_FAIL = "auth.entra_profile_fetch.fail"


class AuthAuditLog(Base):
    """認証監査ログ."""

    __tablename__ = "auth_audit_logs"
    __table_args__ = (
        Index("ix_auth_audit_logs_occurred_at", "occurred_at"),
        Index("ix_auth_audit_logs_event_type_occurred_at", "event_type", "occurred_at"),
        Index("ix_auth_audit_logs_user_id_occurred_at", "user_id", "occurred_at"),
        Index(
            "ix_auth_audit_logs_session_id_occurred_at",
            "session_id",
            "occurred_at",
        ),
        {"schema": "audit"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(start=1, increment=1),
        primary_key=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3),
        nullable=False,
        server_default=text("SYSUTCDATETIME()"),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("auth.sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    xff_raw: Mapped[str | None] = mapped_column(NVARCHAR(length=None), nullable=True)
    connection_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audit_metadata: Mapped[str | None] = mapped_column(
        "metadata",
        NVARCHAR(length=None),
        nullable=True,
    )
