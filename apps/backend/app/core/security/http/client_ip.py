"""HTTP request 向け client IP 解決."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from fastapi import Request

from app.core.settings import get_settings


@dataclass(slots=True)
class ResolvedClientIP:
    """監査ログ保存用の IP 解決結果."""

    client_ip: str | None
    xff_raw: str | None
    connection_ip: str | None


def _normalize_ip(value: str | None) -> str | None:
    """IP 文字列を正規化し、無効値は None を返す."""
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
    """X-Forwarded-For 先頭要素を取り出し、IP として正規化する."""
    if not xff_raw:
        return None
    first = xff_raw.split(",")[0].strip()
    return _normalize_ip(first)


def _is_trusted_proxy(connection_ip: str | None) -> bool:
    """直近接続元 IP が信頼済みプロキシかどうかを判定する."""
    settings = get_settings()
    if not settings.trust_proxy_headers or not connection_ip:
        return False

    candidate = ipaddress.ip_address(connection_ip)
    for cidr in settings.trusted_proxy_cidrs:
        if candidate in ipaddress.ip_network(cidr, strict=False):
            return True
    return False


def resolve_client_ips(request: Request) -> ResolvedClientIP:
    """client_ip / xff_raw / connection_ip を解決する."""
    connection_ip = _normalize_ip(request.client.host if request.client else None)

    raw_xff = request.headers.get("x-forwarded-for")
    xff_raw = raw_xff.strip() if raw_xff and raw_xff.strip() else None
    xff_client_ip = (
        _extract_xff_first_ip(xff_raw) if _is_trusted_proxy(connection_ip) else None
    )

    client_ip = xff_client_ip or connection_ip
    return ResolvedClientIP(
        client_ip=client_ip,
        xff_raw=xff_raw,
        connection_ip=connection_ip,
    )
