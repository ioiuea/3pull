"""
ヘルスチェック向けユーティリティ.

- DATABASE_URL から TCP 接続先 (host/port) を安全に抽出する
"""

from __future__ import annotations

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def _host_port_from_url(
    database_url: str,
    default_port: int = 5432,
) -> tuple[str, int] | None:
    """
    DATABASE_URL から接続先 host/port を抽出する.

    Args:
        database_url: SQLAlchemy 形式の DATABASE_URL
        default_port: URL にポート指定が無い場合の既定ポート

    Returns:
        tuple[str, int] | None:
            - (host, port): 有効な接続先が解決できた場合
            - None: URL が不正、または host/port が不正な場合
    """
    try:
        parsed = make_url(database_url)
    except ArgumentError:
        return None

    host = parsed.host
    if not host:
        return None

    port = parsed.port or default_port
    if not (1 <= port <= 65_535):
        return None

    return host, port
