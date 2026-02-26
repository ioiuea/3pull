"""
Entra ID (OIDC) 接続アダプター.

- Entra OIDC 必須設定の検証を行う
- Authlib の OAuth クライアントを初期化して返す
- Graph API 呼び出しとトークンリフレッシュを提供する
"""

from __future__ import annotations

from functools import lru_cache

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status

from app.core.settings import get_settings

_ENTRA_SCOPE = "openid profile email User.Read offline_access"


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
        client_kwargs={"scope": _ENTRA_SCOPE},
    )
    return oauth


async def refresh_entra_access_token(
    *,
    refresh_token: str,
) -> dict[str, object]:
    """
    Entra の refresh_token grant で新しいアクセストークンを取得する.

    Args:
        refresh_token: 現在のリフレッシュトークン

    Returns:
        dict[str, object]: トークンレスポンス
    """
    settings = get_settings()
    token_url = f"https://login.microsoftonline.com/{settings.entra_tenant_id}/oauth2/v2.0/token"
    form_data = {
        "grant_type": "refresh_token",
        "client_id": settings.entra_client_id or "",
        "client_secret": settings.entra_client_secret or "",
        "refresh_token": refresh_token,
        "scope": _ENTRA_SCOPE,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=form_data)
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "entra_token_refresh_failed", "message": str(error)},
        ) from error

    if response.status_code in (400, 401):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "entra_refresh_token_invalid",
                "message": "Entra refresh token is invalid or expired",
            },
        )

    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "entra_token_refresh_failed",
                "message": (
                    f"Entra token endpoint failed with status {response.status_code}"
                ),
            },
        )

    payload = response.json()
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "entra_token_refresh_invalid_payload",
                "message": "Access token was not included in Entra response",
            },
        )
    return payload


async def fetch_entra_me_profile(
    *,
    access_token: str,
) -> dict[str, str | None]:
    """
    Microsoft Graph `/me` からプロフィールを取得する.

    Args:
        access_token: Entra OIDC で取得した委譲アクセストークン

    Returns:
        dict[str, str | None]: 表示用プロフィール項目

    Raises:
        HTTPException: Graph API 取得失敗時
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me"
                "?$select=displayName,companyName,department,jobTitle,mail,userPrincipalName",
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "graph_request_failed", "message": str(error)},
        ) from error

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "graph_token_invalid",
                "message": "Graph access token is invalid or expired",
            },
        )

    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "graph_profile_fetch_failed",
                "message": f"Graph API failed with status {response.status_code}",
            },
        )

    payload = response.json()
    email = payload.get("mail") or payload.get("userPrincipalName")
    return {
        "displayName": payload.get("displayName"),
        "companyName": payload.get("companyName"),
        "department": payload.get("department"),
        "jobTitle": payload.get("jobTitle"),
        "email": email,
    }
