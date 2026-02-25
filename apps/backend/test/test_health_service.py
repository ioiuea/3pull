from __future__ import annotations

from app.services.health import _host_port_from_url


def test_host_port_from_url_uses_explicit_port() -> None:
    # URL にポート番号が明示されている場合は、その値を優先して返すことを確認する。
    assert _host_port_from_url("postgresql://localhost:6543/app", 5432) == (
        "localhost",
        6543,
    )


def test_host_port_from_url_uses_default_port_when_not_present() -> None:
    # URL にポート番号がない場合は、
    # 引数で渡したデフォルトポートが使われることを確認する。
    assert _host_port_from_url("postgresql://localhost/app", 5432) == (
        "localhost",
        5432,
    )


def test_host_port_from_url_returns_none_on_missing_host() -> None:
    # ホストが欠けた URL は接続先として不正なので、
    # None を返してスキップ判定できることを確認する。
    assert _host_port_from_url("postgresql:///app", 5432) is None


def test_host_port_from_url_returns_none_on_invalid_port() -> None:
    # ポート範囲外 (0-65535 以外) の URL は不正値として扱い、None を返すことを確認する。
    assert _host_port_from_url("postgresql://localhost:99999/app", 5432) is None
