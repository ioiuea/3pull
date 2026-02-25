"""
UserSession モデル向けリポジトリ.

- セッションの発行・参照・失効を扱う
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.session import UserSession


async def create_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    session_token_hash: str,
    expires_at: datetime,
    ip_address: str | None,
    user_agent: str | None,
    entra_access_token: str | None = None,
    entra_refresh_token: str | None = None,
    entra_access_token_expires_at: datetime | None = None,
) -> UserSession:
    """
    セッションを新規発行する.

    Args:
        session: DB セッション
        user_id: ユーザー ID
        session_token_hash: 生トークンのハッシュ値
        expires_at: 有効期限
        ip_address: クライアントIP
        user_agent: User-Agent
        entra_access_token: Entra Graph 用アクセストークン（Entraログイン時のみ）
        entra_refresh_token: Entra リフレッシュトークン（Entraログイン時のみ）
        entra_access_token_expires_at: Entra アクセストークン有効期限

    Returns:
        UserSession: 作成済みセッション
    """
    user_session = UserSession(
        user_id=user_id,
        session_token_hash=session_token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        entra_access_token=entra_access_token,
        entra_refresh_token=entra_refresh_token,
        entra_access_token_expires_at=entra_access_token_expires_at,
    )
    session.add(user_session)
    await session.flush()
    return user_session


async def get_active_session_by_token_hash(
    session: AsyncSession,
    *,
    session_token_hash: str,
    now: datetime,
) -> UserSession | None:
    """
    有効なセッションをトークンハッシュで取得する.

    Args:
        session: DB セッション
        session_token_hash: 生トークンのハッシュ値
        now: 現在時刻（UTC）

    Returns:
        UserSession | None: 有効セッション
    """
    result = await session.execute(
        select(UserSession).where(
            and_(
                UserSession.session_token_hash == session_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(
    session: AsyncSession,
    *,
    session_id: UUID,
    revoked_at: datetime,
) -> None:
    """
    セッションを失効する.

    Args:
        session: DB セッション
        session_id: セッション ID
        revoked_at: 失効時刻
    """
    await session.execute(
        update(UserSession)
        .where(UserSession.id == session_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


async def revoke_all_user_sessions(
    session: AsyncSession,
    *,
    user_id: UUID,
    revoked_at: datetime,
) -> None:
    """
    ユーザーに紐づく未失効セッションを全て失効する.

    Args:
        session: DB セッション
        user_id: ユーザー ID
        revoked_at: 失効時刻
    """
    await session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


async def update_entra_tokens_by_session_id(
    session: AsyncSession,
    *,
    session_id: UUID,
    access_token: str,
    refresh_token: str | None,
    access_token_expires_at: datetime | None,
) -> None:
    """
    セッションに紐づく Entra トークンを更新する.

    Args:
        session: DB セッション
        session_id: セッション ID
        access_token: 新しいアクセストークン
        refresh_token: 新しいリフレッシュトークン（未返却時は None）
        access_token_expires_at: 新しいアクセストークン有効期限
    """
    values: dict[str, object] = {
        "entra_access_token": access_token,
        "entra_access_token_expires_at": access_token_expires_at,
    }
    if refresh_token is not None:
        values["entra_refresh_token"] = refresh_token

    await session.execute(
        update(UserSession)
        .where(UserSession.id == session_id, UserSession.revoked_at.is_(None))
        .values(**values)
    )
