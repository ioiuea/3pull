"""
DB セッション認証サービス.

- セッション発行（生トークン生成 + ハッシュ保存）
- セッション検証（トークンからユーザー解決）
- セッション失効（ログアウト）
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.config import get_logger
from app.core.security.token_cipher import decrypt_token, encrypt_token
from app.core.settings import get_settings
from app.models.auth.session import UserSession
from app.models.auth.user import User
from app.repositories.auth.session_repository import (
    create_session,
    get_active_session_by_token_hash,
    revoke_session,
)
from app.repositories.auth.user_repository import get_user_by_id


class SessionAuthErrorCode(StrEnum):
    """セッション認証エラーコード."""

    SESSION_INVALID = "session_invalid"
    SESSION_EXPIRED = "session_expired"
    USER_NOT_FOUND = "user_not_found"


@dataclass(slots=True)
class SessionAuthError(Exception):
    """
    セッション認証失敗を表す例外.

    Attributes:
        code: エラーコード
        message: 人間可読メッセージ
    """

    code: SessionAuthErrorCode
    message: str


logger = get_logger(__name__)


def _hash_token(raw_token: str) -> str:
    """
    生トークンを SHA-256 ハッシュ化する.

    Args:
        raw_token: 生トークン

    Returns:
        str: 16進文字列ハッシュ
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def issue_user_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    ip_address: str | None,
    user_agent: str | None,
    ttl_seconds: int | None = None,
    entra_access_token: str | None = None,
    entra_refresh_token: str | None = None,
    entra_access_token_expires_at: datetime | None = None,
) -> str:
    """
    ユーザーセッションを発行し、生トークンを返す.

    Args:
        session: DB セッション
        user_id: ユーザー ID
        ip_address: クライアント IP
        user_agent: User-Agent
        ttl_seconds: TTL（秒）。未指定時は設定値を利用
        entra_access_token: Entra Graph 用アクセストークン
        entra_refresh_token: Entra Graph 用リフレッシュトークン
        entra_access_token_expires_at: Entra アクセストークン有効期限

    Returns:
        str: Cookie に設定する生トークン
    """
    settings = get_settings()
    effective_ttl_seconds = ttl_seconds or settings.session_ttl_seconds
    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = now + timedelta(seconds=effective_ttl_seconds)
    await create_session(
        session,
        user_id=user_id,
        session_token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        entra_access_token=encrypt_token(entra_access_token),
        entra_refresh_token=encrypt_token(entra_refresh_token),
        entra_access_token_expires_at=entra_access_token_expires_at,
    )
    return raw_token


async def resolve_active_session_by_token(
    session: AsyncSession,
    *,
    raw_token: str,
) -> UserSession:
    """
    生セッショントークンから有効セッションを解決する.

    Args:
        session: DB セッション
        raw_token: Cookie から受け取った生トークン

    Returns:
        UserSession: 有効セッション
    """
    now = datetime.now(timezone.utc)
    token_hash = _hash_token(raw_token)
    user_session = await get_active_session_by_token_hash(
        session,
        session_token_hash=token_hash,
        now=now,
    )
    if user_session is None:
        raise SessionAuthError(
            code=SessionAuthErrorCode.SESSION_INVALID,
            message="Session is invalid",
        )
    return user_session


async def resolve_user_by_session_token(
    session: AsyncSession,
    *,
    raw_token: str,
) -> User:
    """
    生セッショントークンからユーザーを解決する.

    Args:
        session: DB セッション
        raw_token: Cookie から受け取った生トークン

    Returns:
        User: 認証済みユーザー
    """
    user_session = await resolve_active_session_by_token(session, raw_token=raw_token)

    user = await get_user_by_id(session, user_session.user_id)
    if user is None:
        raise SessionAuthError(
            code=SessionAuthErrorCode.USER_NOT_FOUND,
            message="User is not found",
        )
    return user


async def revoke_session_by_token(
    session: AsyncSession,
    *,
    raw_token: str,
) -> None:
    """
    生セッショントークンに対応するセッションを失効する.

    Args:
        session: DB セッション
        raw_token: Cookie から受け取った生トークン
    """
    now = datetime.now(timezone.utc)
    user_session = await resolve_active_session_by_token(session, raw_token=raw_token)
    await revoke_session(session, session_id=user_session.id, revoked_at=now)
    logger.info(
        "auth.audit.session.revoke",
        session_id=str(user_session.id),
        user_id=str(user_session.user_id),
        reason="logout",
    )


async def refresh_user_session(
    session: AsyncSession,
    *,
    raw_token: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[User, str]:
    """
    既存セッションをローテーションして新しいセッションを発行する.

    Args:
        session: DB セッション
        raw_token: 現在の生セッショントークン
        ip_address: クライアント IP
        user_agent: User-Agent

    Returns:
        tuple[User, str]: 認証ユーザーと新しい生セッショントークン
    """
    now = datetime.now(timezone.utc)
    current_session = await resolve_active_session_by_token(
        session,
        raw_token=raw_token,
    )

    user = await get_user_by_id(session, current_session.user_id)
    if user is None:
        raise SessionAuthError(
            code=SessionAuthErrorCode.USER_NOT_FOUND,
            message="User is not found",
        )

    await revoke_session(session, session_id=current_session.id, revoked_at=now)
    logger.info(
        "auth.audit.session.revoke",
        session_id=str(current_session.id),
        user_id=str(current_session.user_id),
        reason="refresh",
    )
    new_token = await issue_user_session(
        session,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        entra_access_token=decrypt_token(current_session.entra_access_token),
        entra_refresh_token=decrypt_token(current_session.entra_refresh_token),
        entra_access_token_expires_at=current_session.entra_access_token_expires_at,
    )
    return user, new_token
