"""
Azure Managed Redis クライアント生成アダプタ.
"""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from typing import Any

from azure.identity import DefaultAzureCredential
from redis.asyncio import Redis

from app.core.settings import get_settings

_REDIS_ACCESS_TOKEN_SCOPE = "https://redis.azure.com/.default"
_REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = 1.5
_REDIS_SOCKET_TIMEOUT_SECONDS = 1.5


@lru_cache(maxsize=1)
def _get_default_credential() -> DefaultAzureCredential:
    """DefaultAzureCredential をキャッシュして返す."""
    return DefaultAzureCredential()


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """
    JWT の payload を検証なしで展開する.

    Redis 接続 username に使う主体 ID を token claim から取り出す目的だけで使う。
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise RuntimeError("Redis access token is not a valid JWT")

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload + padding)
    return json.loads(decoded)


def _resolve_redis_username(access_token: str) -> str:
    """
    Redis 接続用 username を access token claim から解決する.

    Microsoft Entra 認証では object id 相当を username に使う想定とする。
    """
    payload = _decode_jwt_payload(access_token)
    username = str(payload.get("oid") or payload.get("sub") or "").strip()
    if not username:
        raise RuntimeError("Redis username could not be resolved from access token")
    return username


def _get_redis_access_token() -> str:
    """Azure Managed Redis 用 access token を取得する."""
    credential = _get_default_credential()
    return credential.get_token(_REDIS_ACCESS_TOKEN_SCOPE).token


def create_redis_client() -> Redis:
    """
    Azure Managed Redis クライアントを生成する.
    """
    settings = get_settings()
    if not settings.redis_host:
        raise RuntimeError("REDIS_HOST is required")

    access_token = _get_redis_access_token()
    username = _resolve_redis_username(access_token)

    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        ssl=settings.redis_ssl,
        username=username,
        password=access_token,
        decode_responses=True,
        # Redis 障害時に auth API / health が長時間ハングしないよう、
        # 接続と応答の待ち時間を短く切る。
        socket_connect_timeout=_REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=_REDIS_SOCKET_TIMEOUT_SECONDS,
    )
