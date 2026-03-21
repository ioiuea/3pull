"""認証 API 向け rate limit の Redis ストア.

この層は Redis のキー設計とカウンタ更新だけを担当します。
policy 解釈や HTTP 変換は持たず、service 層からの指示をそのまま実行します。

実装方針:
- counter は Sorted Set を使い、score に epoch milliseconds を保存する
- block は string key + TTL で保持する
- request/failure ともに同じ key ルールで扱う
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
    """request/failure カウンタ用 Redis キーを返す."""
    return f"{_NAMESPACE}:counter:{policy_key.value}:{kind.value}:{client_ip}"


def _block_key(*, policy_key: RateLimitPolicyKey, client_ip: str) -> str:
    """block 状態保持用 Redis キーを返す."""
    return f"{_NAMESPACE}:block:{policy_key.value}:{client_ip}"


def _member(now_ms: int) -> str:
    """Sorted Set の member を一意化して返す."""
    return f"{now_ms}:{uuid4().hex}"


def _now_ms() -> int:
    """現在時刻を epoch milliseconds で返す."""
    return int(time() * 1000)


class RateLimitRedisStore:
    """rate limit 用の Redis 操作を提供する.

    service 層はこのクラスを使って、
    「今 block 中か」「今回のイベントを記録すると何件になるか」を問い合わせます。
    Redis 接続の生成責務もここに閉じ込めています。
    """

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or create_redis_client()

    async def close(self) -> None:
        """内部 Redis client をクローズする."""
        await self._client.aclose()

    async def get_block_ttl_seconds(
        self,
        *,
        policy_key: RateLimitPolicyKey,
        client_ip: str,
    ) -> int | None:
        """block key の残 TTL を秒単位で返す."""
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
        """block key を設定し、一定秒数だけ block 状態を保持する."""
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
        """イベントを 1 件記録し、window 内件数を返す.

        手順は次の通りです。
        1. 観測窓の外に出た古い要素を削除する
        2. 現在イベントを追加する
        3. 窓内件数を数える
        4. key TTL を窓幅に合わせて延長する
        """
        now_ms = _now_ms()
        key = _counter_key(policy_key=policy_key, kind=kind, client_ip=client_ip)
        min_score = now_ms - (window.seconds * 1000)
        ttl_seconds = max(window.seconds, 1)

        async with self._client.pipeline(transaction=True) as pipe:
            # 4 操作を 1 回の pipeline にまとめ、余計な往復を避ける。
            pipe.zremrangebyscore(key, 0, min_score)
            pipe.zadd(key, {_member(now_ms): now_ms})
            pipe.zcount(key, min_score, now_ms)
            pipe.expire(key, ttl_seconds)
            _, _, count, _ = await pipe.execute()
        return int(count)
