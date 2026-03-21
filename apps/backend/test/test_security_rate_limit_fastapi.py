from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.security.rate_limit.fastapi import require_rate_limit
from app.core.security.rate_limit.models import RateLimitPolicyKey


def _build_request(host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": (host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_require_rate_limit_raises_429_when_enforced_blocked(monkeypatch) -> None:
    # 目的: enforced な block 判定を 429 に変換することを保証する。
    decision = SimpleNamespace(blocked=True, enforced=True, reason=None)

    class FakeService:
        response_message = "blocked"

        async def evaluate_request(self, *, policy_key, client_ip):
            return decision

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.core.security.rate_limit.fastapi.RateLimitService",
        FakeService,
    )

    dependency = require_rate_limit(RateLimitPolicyKey.EMAIL_LOGIN)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(_build_request())

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "blocked"


@pytest.mark.asyncio
async def test_require_rate_limit_allows_observe_mode(monkeypatch) -> None:
    # 目的: observe mode の block 判定では通常継続することを保証する。
    decision = SimpleNamespace(blocked=True, enforced=False, reason=None)

    class FakeService:
        response_message = "blocked"

        async def evaluate_request(self, *, policy_key, client_ip):
            return decision

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.core.security.rate_limit.fastapi.RateLimitService",
        FakeService,
    )

    dependency = require_rate_limit(RateLimitPolicyKey.EMAIL_LOGIN)

    await dependency(_build_request())


@pytest.mark.asyncio
async def test_require_rate_limit_fail_open_on_service_error(monkeypatch) -> None:
    # 目的: 判定処理エラー時は fail-open で継続することを保証する。
    class FakeService:
        response_message = "blocked"

        async def evaluate_request(self, *, policy_key, client_ip):
            raise RuntimeError("redis down")

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.core.security.rate_limit.fastapi.RateLimitService",
        FakeService,
    )

    dependency = require_rate_limit(RateLimitPolicyKey.EMAIL_LOGIN)

    await dependency(_build_request())
