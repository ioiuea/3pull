"""
User モデル向けリポジトリ.

- users テーブルへの CRUD を提供する
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth.user import User, UserType


def normalize_email(email: str) -> str:
    """
    メールアドレスを正規化する.

    Args:
        email: 生のメールアドレス

    Returns:
        str: trim + lower を適用した値
    """
    return email.strip().lower()


def get_user_by_email(session: Session, email: str) -> User | None:
    """
    正規化メールアドレスでユーザーを 1 件取得する.

    Args:
        session: DB セッション
        email: メールアドレス

    Returns:
        User | None: 一致ユーザー
    """
    normalized = normalize_email(email)
    result = session.execute(select(User).where(User.email_normalized == normalized))
    return result.scalar_one_or_none()


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    """
    ユーザー ID でユーザーを 1 件取得する.

    Args:
        session: DB セッション
        user_id: ユーザー ID

    Returns:
        User | None: 一致ユーザー
    """
    result = session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def create_user(
    session: Session,
    email: str,
    user_type: UserType,
    display_name: str | None,
) -> User:
    """
    ユーザーを新規作成する.

    Args:
        session: DB セッション
        email: メールアドレス
        user_type: ユーザー種別
        display_name: 表示名

    Returns:
        User: 作成済みユーザー
    """
    normalized_email = normalize_email(email)
    user = User(
        email=email.strip(),
        email_normalized=normalized_email,
        user_type=user_type,
        display_name=display_name,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def update_user_profile(
    session: Session,
    user: User,
    user_type: UserType,
    display_name: str | None,
    email: str | None = None,
) -> User:
    """
    ユーザープロフィールを更新する.

    Args:
        session: DB セッション
        user: 更新対象
        user_type: 更新後ユーザー種別
        display_name: 更新後表示名
        email: 更新後メール（指定時のみ更新）

    Returns:
        User: 更新済みユーザー
    """
    user.user_type = user_type
    if email:
        user.email = email.strip()
        user.email_normalized = normalize_email(email)
    if display_name is not None:
        user.display_name = display_name
    session.add(user)
    session.flush()
    return user
