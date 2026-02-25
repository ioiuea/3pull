"""
Entra ID (OIDC) 接続アダプター.

- Entra OIDC 必須設定の検証を行う
- Authlib の OAuth クライアントを初期化して返す
"""

from __future__ import annotations

from functools import lru_cache

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status

from app.core.settings import get_settings


def validate_entra_settings() -> None:
    """
    Entra OIDC の必須設定値を検証する.

    Raises:
        HTTPException: 必須設定が不足している場合
    """
    settings = get_settings()
    required_values = {
        "ENTRA_TENANT_ID": settings.entra_tenant_id,
        "ENTRA_CLIENT_ID": settings.entra_client_id,
        "ENTRA_CLIENT_SECRET": settings.entra_client_secret,
        "ENTRA_REDIRECT_URI": settings.entra_redirect_uri,
    }
    missing_keys = [key for key, value in required_values.items() if not value]
    if missing_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "entra_configuration_missing",
                "message": f"Missing Entra settings: {', '.join(missing_keys)}",
            },
        )


@lru_cache(maxsize=1)
def get_entra_oauth() -> OAuth:
    """
    Entra 用 OAuth クライアントを初期化して返す.

    Returns:
        OAuth: 初期化済み OAuth クライアント
    """
    settings = get_settings()
    oauth = OAuth()
    oauth.register(
        name="entra",
        client_id=settings.entra_client_id,
        client_secret=settings.entra_client_secret,
        server_metadata_url=(
            f"https://login.microsoftonline.com/"
            f"{settings.entra_tenant_id}/v2.0/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid profile email"},
    )
    return oauth
