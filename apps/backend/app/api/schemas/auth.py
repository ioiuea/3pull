"""
認証 API のスキーマ定義.

- Email signup/login/verify/reset/change の入出力を定義する
- `/auth/me` のユーザー返却形式を定義する
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.auth.auth_audit_log import AuthAuditEventType
from app.models.auth.user import UserType


class AuthErrorResponse(BaseModel):
    """認証 API のエラーレスポンス."""

    code: str
    message: str


class UserMeResponse(BaseModel):
    """`/auth/me` のレスポンス."""

    id: UUID
    email: str
    display_name: str | None
    user_type: UserType
    is_active: bool


class EntraGraphProfileResponse(BaseModel):
    """`/auth/entra/profile` のレスポンス."""

    displayName: str | None
    companyName: str | None
    department: str | None
    jobTitle: str | None
    email: str | None
    access_token_expires_at: datetime | None


class EmailSignupRequest(BaseModel):
    """Email サインアップ要求."""

    email: str
    password: str = Field(min_length=10)
    display_name: str | None = None


class EmailSignupResponse(BaseModel):
    """Email サインアップ応答."""

    status: Literal["verification_required"]
    debug_verification_token: str | None = None


class EmailLoginRequest(BaseModel):
    """Email ログイン要求."""

    email: str
    password: str


class EmailLoginResponse(BaseModel):
    """Email ログイン応答."""

    status: Literal["authenticated"]
    user: UserMeResponse


class EmailVerifyRequest(BaseModel):
    """Email 検証要求."""

    token: str


class EmailVerifyResponse(BaseModel):
    """Email 検証応答."""

    status: Literal["verified"]


class PasswordResetRequestRequest(BaseModel):
    """パスワードリセット要求送信 API の要求."""

    email: str


class PasswordResetRequestResponse(BaseModel):
    """パスワードリセット要求送信 API の応答."""

    status: Literal["accepted"]
    debug_reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    """パスワードリセット確定 API の要求."""

    token: str
    new_password: str = Field(min_length=10)


class PasswordResetConfirmResponse(BaseModel):
    """パスワードリセット確定 API の応答."""

    status: Literal["password_reset"]


class PasswordChangeRequest(BaseModel):
    """パスワード変更 API の要求."""

    current_password: str
    new_password: str = Field(min_length=10)


class PasswordChangeResponse(BaseModel):
    """パスワード変更 API の応答."""

    status: Literal["password_changed"]


class LogoutResponse(BaseModel):
    """ログアウト API の応答."""

    status: Literal["logged_out"]


class SessionRefreshResponse(BaseModel):
    """セッションリフレッシュ API の応答."""

    status: Literal["refreshed"]
    user: UserMeResponse


class AuthAuditLogItemResponse(BaseModel):
    """監査ログ一覧の1行."""

    id: int
    occurred_at: datetime
    event_type: AuthAuditEventType
    user_id: UUID | None
    user_display_name: str | None
    user_email: str | None
    session_id: UUID | None
    provider: str | None
    client_ip: str | None
    xff_raw: str | None
    connection_ip: str | None
    user_agent: str | None
    reason_code: str | None
    metadata: dict[str, object] | None


class AuthAuditLogListResponse(BaseModel):
    """監査ログ一覧 API の応答."""

    page: int
    page_size: int
    total: int
    items: list[AuthAuditLogItemResponse]
