"""認証 API 向け rate limit の型定義.

このファイルは Redis / FastAPI / settings への依存を持たず、
rate limit の判定に必要な最小限の概念だけを表します。

- mode: observe / enforce の運用モード
- policy_key: どの API 種別に対する制御か
- window: 何秒間で何回まで許可するか
- policy: request / failure / block 秒数の組み合わせ
- decision: 最終的な block 判定結果
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RateLimitMode(StrEnum):
    """レート制限モード.

    `OBSERVE` は記録とログだけを行い、実際の block はしません。
    `ENFORCE` は閾値超過時に block を有効化します。
    """

    OBSERVE = "observe"
    ENFORCE = "enforce"


class RateLimitPolicyKey(StrEnum):
    """対象 API ごとの policy 識別子.

    Redis キー名、settings 解決、ログ出力で共通に使う安定キーです。
    path 文字列そのものではなく、API 種別で正規化した名前を使います。
    """

    EMAIL_LOGIN = "email_login"
    ENTRA_LOGIN = "entra_login"
    ENTRA_CALLBACK = "entra_callback"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_CONFIRM = "password_reset_confirm"
    EMAIL_SIGNUP = "email_signup"


class RateLimitCounterKind(StrEnum):
    """カウンタ種別.

    `REQUEST` は単純なアクセス回数、
    `FAILURE` は認証失敗のような失敗イベント回数を表します。
    """

    REQUEST = "req"
    FAILURE = "fail"


class RateLimitReason(StrEnum):
    """判定理由.

    API 層はこの理由を見て詳細挙動を分岐しませんが、
    ログと運用確認のために保持します。
    """

    REQUEST_THRESHOLD_EXCEEDED = "request_threshold_exceeded"
    FAILURE_THRESHOLD_EXCEEDED = "failure_threshold_exceeded"
    ALREADY_BLOCKED = "already_blocked"
    OBSERVED_ONLY = "observed_only"


@dataclass(frozen=True, slots=True)
class RateLimitWindow:
    """窓幅と閾値.

    例: `seconds=60, limit=10` は「直近 60 秒で 10 回まで」を表します。
    複数 window を並べることで、短期/中期の両方を同時に制御できます。
    """

    seconds: int
    limit: int


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """policy 定義.

    1 つの API 種別に対して、
    request 回数・failure 回数・block 秒数をまとめた設定です。
    `failure_windows` が空の場合は、失敗回数ベースの block を行いません。
    """

    key: RateLimitPolicyKey
    request_windows: tuple[RateLimitWindow, ...]
    failure_windows: tuple[RateLimitWindow, ...] = ()
    block_seconds: int = 0


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """判定結果.

    service 層から FastAPI guard へ返す共通結果です。
    `blocked` は「制限対象か」を表し、実際に HTTP 429 を返すかどうかは
    `enforced` を見て最終決定します。
    """

    policy_key: RateLimitPolicyKey
    client_ip: str
    blocked: bool
    enforced: bool
    reason: RateLimitReason | None = None
    retry_after_seconds: int | None = None
