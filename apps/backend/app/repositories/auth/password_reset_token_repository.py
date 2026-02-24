"""
PasswordResetToken モデル向けリポジトリ.

- パスワードリセットトークンの発行・参照・失効を扱う
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.password_reset_token import PasswordResetToken


async def create_password_reset_token(
    session: AsyncSession,
    *,
    identity_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> PasswordResetToken:
    """
    パスワードリセットトークンを発行する.

    Args:
        session: DB セッション
        identity_id: 対象 identity ID
        token_hash: 生トークンのハッシュ値
        expires_at: 有効期限

    Returns:
        PasswordResetToken: 作成済みトークン
    """
    token = PasswordResetToken(
        identity_id=identity_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()
    return token


async def get_password_reset_token_by_hash(
    session: AsyncSession,
    *,
    token_hash: str,
) -> PasswordResetToken | None:
    """
    トークンハッシュでパスワードリセットトークンを取得する.

    Args:
        session: DB セッション
        token_hash: 生トークンのハッシュ値

    Returns:
        PasswordResetToken | None: 一致トークン
    """
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def consume_password_reset_token(
    session: AsyncSession,
    *,
    token: PasswordResetToken,
    consumed_at: datetime,
) -> PasswordResetToken:
    """
    消費済みトークンに consumed_at を設定する.

    Args:
        session: DB セッション
        token: 更新対象トークン
        consumed_at: 消費時刻

    Returns:
        PasswordResetToken: 更新済みトークン
    """
    token.consumed_at = consumed_at
    session.add(token)
    await session.flush()
    return token


async def revoke_active_password_reset_tokens_by_identity_id(
    session: AsyncSession,
    *,
    identity_id: UUID,
    revoked_at: datetime,
) -> None:
    """
    未消費のリセットトークンを失効（consumed扱い）する.

    Args:
        session: DB セッション
        identity_id: 対象 identity ID
        revoked_at: 失効時刻
    """
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.identity_id == identity_id,
            PasswordResetToken.consumed_at.is_(None),
        )
        .values(consumed_at=revoked_at)
    )
