"""
認証モジュール

このモジュールはリクエストヘッダーからユーザー情報を抽出し、
認証済みユーザー情報を提供します。
"""

from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """
    認証済みユーザー情報

    Attributes:
        user_id: ユーザーID
        email: メールアドレス
    """

    user_id: str
    email: str


async def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
) -> AuthenticatedUser:
    """
    リクエストヘッダーから認証済みユーザー情報を取得

    フロントエンドのAuth.jsから送信されるカスタムヘッダー
    （X-User-Id, X-User-Email）を抽出して返します。

    Args:
        x_user_id: X-User-Idヘッダー
        x_user_email: X-User-Emailヘッダー

    Returns:
        AuthenticatedUser: 認証済みユーザー情報

    Raises:
        HTTPException: 認証ヘッダーが不足している場合（401）
    """
    if not x_user_id or not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing X-User-Id or X-User-Email header.",
        )

    return AuthenticatedUser(user_id=x_user_id, email=x_user_email)
