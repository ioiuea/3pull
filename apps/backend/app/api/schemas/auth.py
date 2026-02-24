"""
認証 API のスキーマ定義.

- Email signup/login/verify/reset/change の入出力を定義する
- `/auth/me` のユーザー返却形式を定義する
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

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
