"""
認証 API レート制限向け Redis ストア.
"""

from __future__ import annotations

from time import time
from uuid import uuid4

from redis.asyncio import Redis

from app.adapters.cache import create_redis_client
from app.core.security.rate_limit.models import (
    RateLimitCounterKind,
    RateLimitPolicyKey,
    RateLimitWindow,
)

_NAMESPACE = "auth:ratelimit"


def _counter_key(
    *,
    policy_key: RateLimitPolicyKey,
    kind: RateLimitCounterKind,
    client_ip: str,
) -> str:
    return f"{_NAMESPACE}:counter:{policy_key.value}:{kind.value}:{client_ip}"


def _block_key(*, policy_key: RateLimitPolicyKey, client_ip: str) -> str:
    return f"{_NAMESPACE}:block:{policy_key.value}:{client_ip}"


def _member(now_ms: int) -> str:
    return f"{now_ms}:{uuid4().hex}"


def _now_ms() -> int:
    return int(time() * 1000)


class RateLimitRedisStore:
    """レート制限用の Redis 操作を提供する."""

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or create_redis_client()

    async def close(self) -> None:
        await self._client.aclose()

    async def get_block_ttl_seconds(
        self,
        *,
        policy_key: RateLimitPolicyKey,
        client_ip: str,
    ) -> int | None:
        ttl = await self._client.ttl(
            _block_key(policy_key=policy_key, client_ip=client_ip)
        )
        return ttl if ttl and ttl > 0 else None

    async def set_block(
        self,
        *,
        policy_key: RateLimitPolicyKey,
        client_ip: str,
        block_seconds: int,
        reason: str,
    ) -> None:
        await self._client.set(
            _block_key(policy_key=policy_key, client_ip=client_ip),
            reason,
            ex=block_seconds,
        )

    async def record_and_count(
        self,
        *,
        policy_key: RateLimitPolicyKey,
        kind: RateLimitCounterKind,
        client_ip: str,
        window: RateLimitWindow,
    ) -> int:
        now_ms = _now_ms()
        key = _counter_key(policy_key=policy_key, kind=kind, client_ip=client_ip)
        min_score = now_ms - (window.seconds * 1000)
        ttl_seconds = max(window.seconds, 1)

        async with self._client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, min_score)
            pipe.zadd(key, {_member(now_ms): now_ms})
            pipe.zcount(key, min_score, now_ms)
            pipe.expire(key, ttl_seconds)
            _, _, count, _ = await pipe.execute()
        return int(count)
