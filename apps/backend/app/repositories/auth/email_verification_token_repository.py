"""
EmailVerificationToken モデル向けリポジトリ.

- メール検証トークンの発行・参照・失効を扱う
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.email_verification_token import EmailVerificationToken


async def create_email_verification_token(
    session: AsyncSession,
    *,
    identity_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> EmailVerificationToken:
    """
    メール検証トークンを発行する.

    Args:
        session: DB セッション
        identity_id: 対象 identity ID
        token_hash: 生トークンのハッシュ値
        expires_at: 有効期限

    Returns:
        EmailVerificationToken: 作成済みトークン
    """
    token = EmailVerificationToken(
        identity_id=identity_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()
    return token


async def get_email_verification_token_by_hash(
    session: AsyncSession,
    *,
    token_hash: str,
) -> EmailVerificationToken | None:
    """
    トークンハッシュで検証トークンを取得する.

    Args:
        session: DB セッション
        token_hash: 生トークンのハッシュ値

    Returns:
        EmailVerificationToken | None: 一致トークン
    """
    result = await session.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def consume_email_verification_token(
    session: AsyncSession,
    *,
    token: EmailVerificationToken,
    consumed_at: datetime,
) -> EmailVerificationToken:
    """
    検証済みトークンに consumed_at を設定する.

    Args:
        session: DB セッション
        token: 更新対象トークン
        consumed_at: 消費時刻

    Returns:
        EmailVerificationToken: 更新済みトークン
    """
    token.consumed_at = consumed_at
    session.add(token)
    await session.flush()
    return token


async def revoke_active_tokens_by_identity_id(
    session: AsyncSession,
    *,
    identity_id: UUID,
    revoked_at: datetime,
) -> None:
    """
    未消費の検証トークンを失効（consumed扱い）する.

    Args:
        session: DB セッション
        identity_id: 対象 identity ID
        revoked_at: 失効時刻
    """
    await session.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.identity_id == identity_id,
            EmailVerificationToken.consumed_at.is_(None),
        )
        .values(consumed_at=revoked_at)
    )
