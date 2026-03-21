"""認証 API 向け rate limit dependency."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.logging.config import get_logger
from app.core.security import RateLimitPolicyKey, RateLimitService, resolve_client_ips

logger = get_logger(__name__)


def require_rate_limit(policy_key: RateLimitPolicyKey):
    """対象 policy の request rate limit を適用する dependency を返す."""

    async def dependency(request: Request) -> None:
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
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=service.response_message,
        )

    return dependency
