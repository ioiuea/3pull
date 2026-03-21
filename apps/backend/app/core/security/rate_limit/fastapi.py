"""FastAPI 向け rate limit guard.

このファイルは HTTP レイヤに最も近い adapter です。
service 層が返した `RateLimitDecision` を見て、次を行います。

- Request から client IP を解決する
- service で request 判定を実行する
- Redis 障害などは fail-open で握りつぶす
- observe mode では 429 を返さずログだけ残す
- enforce mode の block 時だけ `HTTPException(429)` に変換する
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.logging.config import get_logger
from app.core.security import RateLimitPolicyKey, RateLimitService, resolve_client_ips

logger = get_logger(__name__)


def require_rate_limit(policy_key: RateLimitPolicyKey):
    """対象 policy の request rate limit を適用する dependency を返す.

    router 側では `Depends(require_rate_limit(...))` として使います。
    各 endpoint は policy_key だけを意識し、Redis や block 判定の詳細は持ちません。
    """

    async def dependency(request: Request) -> None:
        # client IP が解決できない場合は誤判定を避けるため fail-open に倒す。
        resolved_ips = resolve_client_ips(request)
        client_ip = resolved_ips.client_ip
        if client_ip is None:
            logger.warning(
                "auth.rate_limit.client_ip_unresolved",
                policy_key=policy_key.value,
            )
            return

        service = RateLimitService()
        try:
            decision = await service.evaluate_request(
                policy_key=policy_key,
                client_ip=client_ip,
            )
        except Exception as error:
            # Redis 障害などで認証導線を全面停止させないよう、
            # 仕様どおり fail-open にする。
            logger.warning(
                "auth.rate_limit.request_check_failed",
                policy_key=policy_key.value,
                client_ip=client_ip,
                reason=str(error),
            )
            return
        finally:
            await service.close()

        if not decision.blocked:
            return

        if not decision.enforced:
            # observe mode では block 相当の事象を記録するだけで、HTTP 応答は継続する。
            logger.info(
                "auth.rate_limit.observed_only",
                policy_key=policy_key.value,
                client_ip=client_ip,
                reason=decision.reason.value if decision.reason else None,
            )
            return

        logger.warning(
            "auth.rate_limit.blocked",
            policy_key=policy_key.value,
            client_ip=client_ip,
            reason=decision.reason.value if decision.reason else None,
        )
        # enforce mode のみ 429 へ変換する。
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=service.response_message,
        )

    return dependency
