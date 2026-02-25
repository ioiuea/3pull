"""
AuthIdentity モデル向けリポジトリ.

- auth_identities テーブルへの CRUD を提供する
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.auth_identity import AuthIdentity, AuthProvider


async def get_identity_by_provider_subject(
    session: AsyncSession,
    provider: AuthProvider,
    provider_subject: str,
) -> AuthIdentity | None:
    """
    provider + provider_subject で認証アイデンティティを取得する.

    Args:
        session: DB セッション
        provider: 認証プロバイダー
        provider_subject: プロバイダー側 subject

    Returns:
        AuthIdentity | None: 一致アイデンティティ
    """
    result = await session.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.provider_subject == provider_subject,
        )
    )
    return result.scalar_one_or_none()


async def get_identity_by_id(
    session: AsyncSession,
    identity_id: UUID,
) -> AuthIdentity | None:
    """
    identity_id で認証アイデンティティを取得する.

    Args:
        session: DB セッション
        identity_id: 認証アイデンティティ ID

    Returns:
        AuthIdentity | None: 一致アイデンティティ
    """
    result = await session.execute(
        select(AuthIdentity).where(AuthIdentity.id == identity_id)
    )
    return result.scalar_one_or_none()


async def get_identity_by_user_and_provider(
    session: AsyncSession,
    user_id: UUID,
    provider: AuthProvider,
) -> AuthIdentity | None:
    """
    user_id + provider で認証アイデンティティを取得する.

    Args:
        session: DB セッション
        user_id: ユーザー ID
        provider: 認証プロバイダー

    Returns:
        AuthIdentity | None: 一致アイデンティティ
    """
    result = await session.execute(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user_id,
            AuthIdentity.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def create_identity(
    session: AsyncSession,
    user_id: UUID,
    provider: AuthProvider,
    provider_subject: str,
    email_normalized: str,
    password_hash: str | None = None,
) -> AuthIdentity:
    """
    認証アイデンティティを作成する.

    Args:
        session: DB セッション
        user_id: ユーザー ID
        provider: 認証プロバイダー
        provider_subject: プロバイダー側 subject
        email_normalized: 正規化メール
        password_hash: パスワードハッシュ（email provider のみ）

    Returns:
        AuthIdentity: 作成済みアイデンティティ
    """
    identity = AuthIdentity(
        user_id=user_id,
        provider=provider,
        provider_subject=provider_subject,
        email_normalized=email_normalized,
        password_hash=password_hash,
    )
    session.add(identity)
    await session.flush()
    return identity


async def get_identity_by_provider_and_email(
    session: AsyncSession,
    provider: AuthProvider,
    email_normalized: str,
) -> AuthIdentity | None:
    """
    provider + email_normalized で認証アイデンティティを取得する.

    Args:
        session: DB セッション
        provider: 認証プロバイダー
        email_normalized: 正規化メール

    Returns:
        AuthIdentity | None: 一致アイデンティティ
    """
    result = await session.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.email_normalized == email_normalized,
        )
    )
    return result.scalar_one_or_none()


async def mark_email_verified(
    session: AsyncSession,
    identity: AuthIdentity,
) -> AuthIdentity:
    """
    Email identity の検証完了時刻を更新する.

    Args:
        session: DB セッション
        identity: 更新対象 identity

    Returns:
        AuthIdentity: 更新済み identity
    """
    identity.email_verified_at = datetime.now(timezone.utc)
    session.add(identity)
    await session.flush()
    return identity


async def update_password_hash(
    session: AsyncSession,
    *,
    identity: AuthIdentity,
    password_hash: str,
) -> AuthIdentity:
    """
    Email identity のパスワードハッシュを更新する.

    Args:
        session: DB セッション
        identity: 更新対象 identity
        password_hash: 新しいパスワードハッシュ

    Returns:
        AuthIdentity: 更新済み identity
    """
    identity.password_hash = password_hash
    session.add(identity)
    await session.flush()
    return identity


async def record_failed_email_login(
    session: AsyncSession,
    *,
    identity: AuthIdentity,
    max_failures: int,
    lock_minutes: int,
) -> AuthIdentity:
    """
    Email ログイン失敗を記録し、閾値到達時はロック期限を設定する.

    Args:
        session: DB セッション
        identity: 更新対象 identity
        max_failures: ロック発動までの失敗回数
        lock_minutes: ロック継続時間（分）

    Returns:
        AuthIdentity: 更新済み identity
    """
    now = datetime.now(timezone.utc)
    # ロック期限を過ぎていた場合はカウンタをリセットして再計測する。
    if identity.locked_until is not None and identity.locked_until <= now:
        identity.failed_login_count = 0
        identity.locked_until = None

    identity.failed_login_count += 1
    if identity.failed_login_count >= max_failures:
        identity.locked_until = now + timedelta(minutes=lock_minutes)
        identity.failed_login_count = 0

    session.add(identity)
    await session.flush()
    return identity


async def reset_failed_email_login_state(
    session: AsyncSession,
    *,
    identity: AuthIdentity,
) -> AuthIdentity:
    """
    Email ログイン成功時に失敗カウンタとロック状態を解除する.

    Args:
        session: DB セッション
        identity: 更新対象 identity

    Returns:
        AuthIdentity: 更新済み identity
    """
    identity.failed_login_count = 0
    identity.locked_until = None
    identity.last_login_at = datetime.now(timezone.utc)
    session.add(identity)
    await session.flush()
    return identity


async def delete_identity_by_id(session: AsyncSession, identity_id: UUID) -> None:
    """
    認証アイデンティティを削除する.

    Args:
        session: DB セッション
        identity_id: 認証アイデンティティ ID
    """
    await session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity_id))
