"""認証 API 向け rate limit の型定義."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RateLimitMode(StrEnum):
    """レート制限モード."""

    OBSERVE = "observe"
    ENFORCE = "enforce"


class RateLimitPolicyKey(StrEnum):
    """対象 API ごとの policy 識別子."""

    EMAIL_LOGIN = "email_login"
    EMAIL_VERIFY_RESEND = "email_verify_resend"
    ENTRA_LOGIN = "entra_login"
    ENTRA_CALLBACK = "entra_callback"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_CONFIRM = "password_reset_confirm"
    EMAIL_SIGNUP = "email_signup"


class RateLimitCounterKind(StrEnum):
    """カウンタ種別."""

    REQUEST = "req"
    FAILURE = "fail"


class RateLimitReason(StrEnum):
    """判定理由."""

    REQUEST_THRESHOLD_EXCEEDED = "request_threshold_exceeded"
    FAILURE_THRESHOLD_EXCEEDED = "failure_threshold_exceeded"
    ALREADY_BLOCKED = "already_blocked"
    OBSERVED_ONLY = "observed_only"


@dataclass(frozen=True, slots=True)
class RateLimitWindow:
    """窓幅と閾値."""

    seconds: int
    limit: int


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """policy 定義."""

    key: RateLimitPolicyKey
    request_windows: tuple[RateLimitWindow, ...]
    failure_windows: tuple[RateLimitWindow, ...] = ()
    block_seconds: int = 0


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """判定結果."""

    policy_key: RateLimitPolicyKey
    client_ip: str
    blocked: bool
    enforced: bool
    reason: RateLimitReason | None = None
    retry_after_seconds: int | None = None
