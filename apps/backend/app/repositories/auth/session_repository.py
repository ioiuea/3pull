"""
UserSession モデル向けリポジトリ.

- セッションの発行・参照・失効を扱う
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.orm import Session

from app.models.auth.session import UserSession


def create_session(
    session: Session,
    *,
    user_id: UUID,
    session_token_hash: str,
    expires_at: datetime,
    ip_address: str | None,
    user_agent: str | None,
    entra_access_token: str | None = None,
    entra_refresh_token: str | None = None,
    entra_access_token_expires_at: datetime | None = None,
    auth_identity_id: UUID | None = None,
) -> UserSession:
    """
    セッションを新規発行する.
    """
    user_session = UserSession(
        user_id=user_id,
        auth_identity_id=auth_identity_id,
        session_token_hash=session_token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        entra_access_token=entra_access_token,
        entra_refresh_token=entra_refresh_token,
        entra_access_token_expires_at=entra_access_token_expires_at,
    )
    session.add(user_session)
    session.flush()
    return user_session


def get_active_session_by_token_hash(
    session: Session,
    *,
    session_token_hash: str,
    now: datetime,
) -> UserSession | None:
    """
    有効なセッションをトークンハッシュで取得する.
    """
    result = session.execute(
        select(UserSession).where(
            and_(
                UserSession.session_token_hash == session_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
        )
    )
    return result.scalar_one_or_none()


def revoke_session(
    session: Session,
    *,
    session_id: UUID,
    revoked_at: datetime,
) -> None:
    """
    セッションを失効する.
    """
    session.execute(
        update(UserSession)
        .where(UserSession.id == session_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


def revoke_all_user_sessions(
    session: Session,
    *,
    user_id: UUID,
    revoked_at: datetime,
) -> None:
    """
    ユーザーに紐づく未失効セッションを全て失効する.
    """
    session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


def update_entra_tokens_by_session_id(
    session: Session,
    *,
    session_id: UUID,
    access_token: str,
    refresh_token: str | None,
    access_token_expires_at: datetime | None,
) -> None:
    """
    セッションに紐づく Entra トークンを更新する.
    """
    values: dict[str, object] = {
        "entra_access_token": access_token,
        "entra_access_token_expires_at": access_token_expires_at,
    }
    if refresh_token is not None:
        values["entra_refresh_token"] = refresh_token

    session.execute(
        update(UserSession)
        .where(UserSession.id == session_id, UserSession.revoked_at.is_(None))
        .values(**values)
    )


def count_expired_sessions_for_cleanup(
    session: Session,
    *,
    expires_before: datetime,
) -> int:
    """
    cleanup 対象となる期限切れセッション件数を返す.
    """
    result = session.execute(
        select(func.count(UserSession.id)).where(
            UserSession.expires_at < expires_before
        )
    )
    return int(result.scalar_one())


def delete_expired_sessions_batch(
    session: Session,
    *,
    expires_before: datetime,
    batch_size: int,
) -> int:
    """
    期限切れセッションをバッチ単位で削除する.
    """
    target_ids_result = session.execute(
        select(UserSession.id)
        .where(UserSession.expires_at < expires_before)
        .order_by(UserSession.expires_at.asc())
        .limit(batch_size)
    )
    target_ids = list(target_ids_result.scalars().all())
    if not target_ids:
        return 0

    session.execute(delete(UserSession).where(UserSession.id.in_(target_ids)))
    return len(target_ids)
