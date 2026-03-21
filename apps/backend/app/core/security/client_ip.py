"""
監査ログ向けのクライアントIP解決.

- 本番想定: X-Forwarded-For 先頭を client_ip として採用
- ローカル想定: X-Forwarded-For が無い場合は request.client.host を採用
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from fastapi import Request

from app.core.settings import get_settings


@dataclass(slots=True)
class ResolvedClientIP:
    """
    監査ログ保存用のIP解決結果.

    Attributes:
        client_ip: 実クライアントIP（優先: XFF先頭、fallback: connection_ip）
        xff_raw: X-Forwarded-For 生値
        connection_ip: 直近接続元IP（request.client.host）
    """

    client_ip: str | None
    xff_raw: str | None
    connection_ip: str | None


def _normalize_ip(value: str | None) -> str | None:
    """
    IP文字列を正規化し、無効値は None を返す.
    """
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _extract_xff_first_ip(xff_raw: str | None) -> str | None:
    """
    X-Forwarded-For 先頭要素を取り出し、IPとして正規化する.
    """
    if not xff_raw:
        return None
    first = xff_raw.split(",")[0].strip()
    return _normalize_ip(first)


def _is_trusted_proxy(connection_ip: str | None) -> bool:
    """
    直近接続元IPが信頼済みプロキシかどうかを判定する.
    """
    settings = get_settings()
    if not settings.trust_proxy_headers or not connection_ip:
        return False

    candidate = ipaddress.ip_address(connection_ip)
    for cidr in settings.trusted_proxy_cidrs:
        if candidate in ipaddress.ip_network(cidr, strict=False):
            return True
    return False


def resolve_client_ips(request: Request) -> ResolvedClientIP:
    """
    監査ログ仕様に沿って client_ip / xff_raw / connection_ip を解決する.
    """
    connection_ip = _normalize_ip(request.client.host if request.client else None)

    raw_xff = request.headers.get("x-forwarded-for")
    xff_raw = raw_xff.strip() if raw_xff and raw_xff.strip() else None
    xff_client_ip = (
        _extract_xff_first_ip(xff_raw) if _is_trusted_proxy(connection_ip) else None
    )

    # 信頼済みプロキシ配下で有効な XFF がある場合のみ先頭IPを採用する。
    # それ以外は connection_ip を client_ip に採用する。
    client_ip = xff_client_ip or connection_ip
    return ResolvedClientIP(
        client_ip=client_ip,
        xff_raw=xff_raw,
        connection_ip=connection_ip,
    )
