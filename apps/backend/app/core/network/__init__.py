"""
リクエスト由来のネットワーク情報ユーティリティ.
"""

from app.core.network.client_ip import ResolvedClientIP, resolve_client_ips

__all__ = ["ResolvedClientIP", "resolve_client_ips"]
