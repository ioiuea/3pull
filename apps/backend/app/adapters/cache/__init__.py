"""
Redis 接続アダプターパッケージ.
"""

from app.adapters.cache.redis_client import create_redis_client

__all__ = ["create_redis_client"]
