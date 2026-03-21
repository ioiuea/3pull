"""
認証 API レート制限サービス.
"""

from __future__ import annotations

from app.core.security.rate_limit.models import (
    RateLimitCounterKind,
    RateLimitDecision,
    RateLimitMode,
    RateLimitPolicy,
    RateLimitPolicyKey,
    RateLimitReason,
    RateLimitWindow,
)
from app.core.security.rate_limit.store import RateLimitRedisStore
from app.core.settings import get_settings

RATE_LIMIT_RESPONSE_MESSAGE = (
    "Access to this function is currently restricted. Please contact support."
)


def build_rate_limit_policies() -> dict[RateLimitPolicyKey, RateLimitPolicy]:
    """設定値から policy 一覧を構築する."""
    settings = get_settings()
    return {
        RateLimitPolicyKey.EMAIL_LOGIN: RateLimitPolicy(
            key=RateLimitPolicyKey.EMAIL_LOGIN,
            request_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_email_login_request_window_1_seconds,
                    limit=settings.rate_limit_policy_email_login_request_window_1_max_requests,
                ),
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_email_login_request_window_2_seconds,
                    limit=settings.rate_limit_policy_email_login_request_window_2_max_requests,
                ),
            ),
            failure_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_email_login_failure_window_seconds,
                    limit=settings.rate_limit_policy_email_login_max_failures,
                ),
            ),
            block_seconds=settings.rate_limit_policy_email_login_block_seconds,
        ),
        RateLimitPolicyKey.ENTRA_LOGIN: RateLimitPolicy(
            key=RateLimitPolicyKey.ENTRA_LOGIN,
            request_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_entra_login_request_window_1_seconds,
                    limit=settings.rate_limit_policy_entra_login_request_window_1_max_requests,
                ),
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_entra_login_request_window_2_seconds,
                    limit=settings.rate_limit_policy_entra_login_request_window_2_max_requests,
                ),
            ),
            block_seconds=settings.rate_limit_policy_entra_login_block_seconds,
        ),
        RateLimitPolicyKey.ENTRA_CALLBACK: RateLimitPolicy(
            key=RateLimitPolicyKey.ENTRA_CALLBACK,
            request_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_entra_callback_request_window_1_seconds,
                    limit=settings.rate_limit_policy_entra_callback_request_window_1_max_requests,
                ),
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_entra_callback_request_window_2_seconds,
                    limit=settings.rate_limit_policy_entra_callback_request_window_2_max_requests,
                ),
            ),
            failure_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_entra_callback_failure_window_seconds,
                    limit=settings.rate_limit_policy_entra_callback_max_failures,
                ),
            ),
            block_seconds=settings.rate_limit_policy_entra_callback_block_seconds,
        ),
        RateLimitPolicyKey.PASSWORD_RESET_REQUEST: RateLimitPolicy(
            key=RateLimitPolicyKey.PASSWORD_RESET_REQUEST,
            request_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_password_reset_request_window_seconds,
                    limit=settings.rate_limit_policy_password_reset_request_max_requests,
                ),
            ),
            block_seconds=settings.rate_limit_policy_password_reset_request_block_seconds,
        ),
        RateLimitPolicyKey.PASSWORD_RESET_CONFIRM: RateLimitPolicy(
            key=RateLimitPolicyKey.PASSWORD_RESET_CONFIRM,
            request_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_password_reset_confirm_window_seconds,
                    limit=settings.rate_limit_policy_password_reset_confirm_max_requests,
                ),
            ),
            failure_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_password_reset_confirm_failure_window_seconds,
                    limit=settings.rate_limit_policy_password_reset_confirm_max_failures,
                ),
            ),
            block_seconds=settings.rate_limit_policy_password_reset_confirm_block_seconds,
        ),
        RateLimitPolicyKey.EMAIL_SIGNUP: RateLimitPolicy(
            key=RateLimitPolicyKey.EMAIL_SIGNUP,
            request_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_email_signup_request_window_1_seconds,
                    limit=settings.rate_limit_policy_email_signup_request_window_1_max_requests,
                ),
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_email_signup_request_window_2_seconds,
                    limit=settings.rate_limit_policy_email_signup_request_window_2_max_requests,
                ),
            ),
            failure_windows=(
                RateLimitWindow(
                    seconds=settings.rate_limit_policy_email_signup_failure_window_seconds,
                    limit=settings.rate_limit_policy_email_signup_max_failures,
                ),
            ),
            block_seconds=settings.rate_limit_policy_email_signup_block_seconds,
        ),
    }


class RateLimitService:
    """request / failure のレート制限判定を提供する."""

    def __init__(
        self,
        *,
        store: RateLimitRedisStore | None = None,
        policies: dict[RateLimitPolicyKey, RateLimitPolicy] | None = None,
    ) -> None:
        self._store = store or RateLimitRedisStore()
        self._policies = policies or build_rate_limit_policies()

    async def close(self) -> None:
        await self._store.close()

    async def evaluate_request(
        self,
        *,
        policy_key: RateLimitPolicyKey,
        client_ip: str,
    ) -> RateLimitDecision:
        policy = self._policies[policy_key]
        existing_ttl = await self._store.get_block_ttl_seconds(
            policy_key=policy_key,
            client_ip=client_ip,
        )
        if existing_ttl is not None:
            return RateLimitDecision(
                policy_key=policy_key,
                client_ip=client_ip,
                blocked=True,
                enforced=self._mode is RateLimitMode.ENFORCE,
                reason=RateLimitReason.ALREADY_BLOCKED,
                retry_after_seconds=existing_ttl,
            )

        for window in policy.request_windows:
            count = await self._store.record_and_count(
                policy_key=policy_key,
                kind=RateLimitCounterKind.REQUEST,
                client_ip=client_ip,
                window=window,
            )
            if count > window.limit:
                await self._store.set_block(
                    policy_key=policy_key,
                    client_ip=client_ip,
                    block_seconds=policy.block_seconds,
                    reason=RateLimitReason.REQUEST_THRESHOLD_EXCEEDED.value,
                )
                return RateLimitDecision(
                    policy_key=policy_key,
                    client_ip=client_ip,
                    blocked=True,
                    enforced=self._mode is RateLimitMode.ENFORCE,
                    reason=RateLimitReason.REQUEST_THRESHOLD_EXCEEDED,
                    retry_after_seconds=policy.block_seconds,
                )

        return RateLimitDecision(
            policy_key=policy_key,
            client_ip=client_ip,
            blocked=False,
            enforced=False,
            reason=None,
            retry_after_seconds=None,
        )

    async def record_failure(
        self,
        *,
        policy_key: RateLimitPolicyKey,
        client_ip: str,
    ) -> RateLimitDecision:
        policy = self._policies[policy_key]
        if not policy.failure_windows:
            return RateLimitDecision(
                policy_key=policy_key,
                client_ip=client_ip,
                blocked=False,
                enforced=False,
                reason=None,
            )

        for window in policy.failure_windows:
            count = await self._store.record_and_count(
                policy_key=policy_key,
                kind=RateLimitCounterKind.FAILURE,
                client_ip=client_ip,
                window=window,
            )
            if count > window.limit:
                await self._store.set_block(
                    policy_key=policy_key,
                    client_ip=client_ip,
                    block_seconds=policy.block_seconds,
                    reason=RateLimitReason.FAILURE_THRESHOLD_EXCEEDED.value,
                )
                return RateLimitDecision(
                    policy_key=policy_key,
                    client_ip=client_ip,
                    blocked=True,
                    enforced=self._mode is RateLimitMode.ENFORCE,
                    reason=RateLimitReason.FAILURE_THRESHOLD_EXCEEDED,
                    retry_after_seconds=policy.block_seconds,
                )

        return RateLimitDecision(
            policy_key=policy_key,
            client_ip=client_ip,
            blocked=False,
            enforced=False,
            reason=None,
        )

    @property
    def mode(self) -> RateLimitMode:
        return self._mode

    @property
    def response_message(self) -> str:
        return RATE_LIMIT_RESPONSE_MESSAGE

    @property
    def _mode(self) -> RateLimitMode:
        return RateLimitMode(get_settings().rate_limit_mode)
