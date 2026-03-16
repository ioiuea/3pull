"""
EmailVerificationToken モデル向けリポジトリ.

- メール検証トークンの発行・参照・失効を扱う
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.auth.email_verification_token import EmailVerificationToken


def create_email_verification_token(
    session: Session,
    *,
    identity_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> EmailVerificationToken:
    """メール検証トークンを発行する."""
    token = EmailVerificationToken(
        identity_id=identity_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    session.flush()
    return token


def get_email_verification_token_by_hash(
    session: Session,
    *,
    token_hash: str,
) -> EmailVerificationToken | None:
    """トークンハッシュで検証トークンを取得する."""
    result = session.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
    )
    return result.scalar_one_or_none()


def consume_email_verification_token(
    session: Session,
    *,
    token: EmailVerificationToken,
    consumed_at: datetime,
) -> EmailVerificationToken:
    """検証済みトークンに consumed_at を設定する."""
    token.consumed_at = consumed_at
    session.add(token)
    session.flush()
    return token


def revoke_active_tokens_by_identity_id(
    session: Session,
    *,
    identity_id: UUID,
    revoked_at: datetime,
) -> None:
    """未消費の検証トークンを失効する."""
    session.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.identity_id == identity_id,
            EmailVerificationToken.consumed_at.is_(None),
        )
        .values(consumed_at=revoked_at)
    )
