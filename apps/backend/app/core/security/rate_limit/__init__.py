"""認証 API 向け rate limit パッケージ.

このパッケージは、認証系 API に対する IP ベース rate limit を
`core/security` 配下へ集約するための公開入口です。

- `models.py`: policy / decision / enum などの純粋な型定義
- `store.py`: Redis への永続化とカウンタ操作
- `service.py`: policy 適用と block 判定
- `fastapi.py`: FastAPI dependency として使う guard

router からはこの配下の `fastapi.py` もしくは再 export 済みの型だけを使い、
HTTP 以外の詳細を直接持ち込まない前提です。
"""

from app.core.security.rate_limit.models import (
    RateLimitDecision,
    RateLimitMode,
    RateLimitPolicy,
    RateLimitPolicyKey,
    RateLimitReason,
    RateLimitWindow,
)
from app.core.security.rate_limit.service import (
    RateLimitService,
    build_rate_limit_policies,
)
from app.core.security.rate_limit.store import RateLimitRedisStore

__all__ = [
    "RateLimitDecision",
    "RateLimitMode",
    "RateLimitPolicy",
    "RateLimitPolicyKey",
    "RateLimitReason",
    "RateLimitRedisStore",
    "RateLimitService",
    "RateLimitWindow",
    "build_rate_limit_policies",
]
