"""
AuthIdentity モデル向けリポジトリ.

- auth_identities テーブルへの CRUD を提供する
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.auth.auth_identity import AuthIdentity, AuthProvider


def get_identity_by_provider_subject(
    session: Session,
    provider: AuthProvider,
    provider_subject: str,
) -> AuthIdentity | None:
    """
    provider + provider_subject で認証アイデンティティを取得する.
    """
    result = session.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.provider_subject == provider_subject,
        )
    )
    return result.scalar_one_or_none()


def get_identity_by_id(
    session: Session,
    identity_id: UUID,
) -> AuthIdentity | None:
    """
    identity_id で認証アイデンティティを取得する.
    """
    result = session.execute(select(AuthIdentity).where(AuthIdentity.id == identity_id))
    return result.scalar_one_or_none()


def get_identity_by_user_and_provider(
    session: Session,
    user_id: UUID,
    provider: AuthProvider,
) -> AuthIdentity | None:
    """
    user_id + provider で認証アイデンティティを取得する.
    """
    result = session.execute(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user_id,
            AuthIdentity.provider == provider,
        )
    )
    return result.scalar_one_or_none()


def create_identity(
    session: Session,
    user_id: UUID,
    provider: AuthProvider,
    provider_subject: str,
    email_normalized: str,
    password_hash: str | None = None,
) -> AuthIdentity:
    """
    認証アイデンティティを作成する.
    """
    identity = AuthIdentity(
        user_id=user_id,
        provider=provider,
        provider_subject=provider_subject,
        email_normalized=email_normalized,
        password_hash=password_hash,
    )
    session.add(identity)
    session.flush()
    return identity


def get_identity_by_provider_and_email(
    session: Session,
    provider: AuthProvider,
    email_normalized: str,
) -> AuthIdentity | None:
    """
    provider + email_normalized で認証アイデンティティを取得する.
    """
    result = session.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.email_normalized == email_normalized,
        )
    )
    return result.scalar_one_or_none()


def mark_email_verified(
    session: Session,
    identity: AuthIdentity,
) -> AuthIdentity:
    """
    Email identity の検証完了時刻を更新する.
    """
    identity.email_verified_at = datetime.now(timezone.utc)
    session.add(identity)
    session.flush()
    return identity


def update_password_hash(
    session: Session,
    *,
    identity: AuthIdentity,
    password_hash: str,
) -> AuthIdentity:
    """
    Email identity のパスワードハッシュを更新する.
    """
    identity.password_hash = password_hash
    session.add(identity)
    session.flush()
    return identity


def record_failed_email_login(
    session: Session,
    *,
    identity: AuthIdentity,
    max_failures: int,
    lock_minutes: int,
) -> AuthIdentity:
    """
    Email ログイン失敗を記録し、閾値到達時はロック期限を設定する.
    """
    now = datetime.now(timezone.utc)
    if identity.locked_until is not None and identity.locked_until <= now:
        identity.failed_login_count = 0
        identity.locked_until = None

    identity.failed_login_count += 1
    if identity.failed_login_count >= max_failures:
        identity.locked_until = now + timedelta(minutes=lock_minutes)
        identity.failed_login_count = 0

    session.add(identity)
    session.flush()
    return identity


def reset_failed_email_login_state(
    session: Session,
    *,
    identity: AuthIdentity,
) -> AuthIdentity:
    """
    Email ログイン成功時に失敗カウンタとロック状態を解除する.
    """
    identity.failed_login_count = 0
    identity.locked_until = None
    identity.last_login_at = datetime.now(timezone.utc)
    session.add(identity)
    session.flush()
    return identity


def delete_identity_by_id(session: Session, identity_id: UUID) -> None:
    """
    認証アイデンティティを削除する.
    """
    session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity_id))
