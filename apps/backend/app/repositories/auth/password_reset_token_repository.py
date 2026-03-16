"""
PasswordResetToken モデル向けリポジトリ.

- パスワードリセットトークンの発行・参照・失効を扱う
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.auth.password_reset_token import PasswordResetToken


def create_password_reset_token(
    session: Session,
    *,
    identity_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    """パスワードリセットトークンを発行する."""
    token = PasswordResetToken(
        identity_id=identity_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    session.flush()
    return token


def get_password_reset_token_by_hash(
    session: Session,
    *,
    token_hash: str,
) -> PasswordResetToken | None:
    """トークンハッシュでパスワードリセットトークンを取得する."""
    result = session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


def consume_password_reset_token(
    session: Session,
    *,
    token: PasswordResetToken,
    consumed_at: datetime,
) -> PasswordResetToken:
    """消費済みトークンに consumed_at を設定する."""
    token.consumed_at = consumed_at
    session.add(token)
    session.flush()
    return token


def revoke_active_password_reset_tokens_by_identity_id(
    session: Session,
    *,
    identity_id: UUID,
    revoked_at: datetime,
) -> None:
    """未消費のリセットトークンを失効する."""
    session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.identity_id == identity_id,
            PasswordResetToken.consumed_at.is_(None),
        )
        .values(consumed_at=revoked_at)
    )
