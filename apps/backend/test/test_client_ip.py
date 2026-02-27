from __future__ import annotations

from starlette.requests import Request

from app.core.security.client_ip import resolve_client_ips


def _build_request(
    *,
    host: str = "127.0.0.1",
    xff: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode("utf-8")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": (host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_resolve_client_ips_without_xff_uses_connection_ip() -> None:
    # 目的: X-Forwarded-For がない場合の基準IP解決仕様を固定する。
    # 条件: connection host のみを持つリクエストを渡す。
    # 期待値: client_ip/connection_ip は同値、xff_raw は None になる。
    request = _build_request(host="127.0.0.1")

    resolved = resolve_client_ips(request)

    assert resolved.client_ip == "127.0.0.1"
    assert resolved.connection_ip == "127.0.0.1"
    assert resolved.xff_raw is None


def test_resolve_client_ips_with_xff_uses_first_hop() -> None:
    # 目的: XFF がある場合は先頭ホップを client_ip とする仕様を固定する。
    # 条件: xff="203.0.113.9, 10.1.2.3" を含むリクエストを渡す。
    # 期待値: client_ip は 203.0.113.9、connection_ip は socket 接続元のままになる。
    request = _build_request(host="10.0.0.10", xff="203.0.113.9, 10.1.2.3")

    resolved = resolve_client_ips(request)

    assert resolved.client_ip == "203.0.113.9"
    assert resolved.connection_ip == "10.0.0.10"
    assert resolved.xff_raw == "203.0.113.9, 10.1.2.3"


def test_resolve_client_ips_with_invalid_xff_falls_back_to_connection_ip() -> None:
    # 目的: 不正な XFF 先頭値のときに connection_ip へフォールバックする仕様を固定する。
    # 条件: xff 先頭を "unknown" にしたリクエストを渡す。
    # 期待値: client_ip は connection_ip と同値になり、xff_raw は保持される。
    request = _build_request(host="10.0.0.10", xff="unknown, 10.1.2.3")

    resolved = resolve_client_ips(request)

    assert resolved.client_ip == "10.0.0.10"
    assert resolved.connection_ip == "10.0.0.10"
    assert resolved.xff_raw == "unknown, 10.1.2.3"
