from __future__ import annotations

from app.api.routers.health import _host_port_from_url


def test_host_port_from_url_uses_explicit_port() -> None:
    # 目的: URL に明示ポートがある場合の優先ルールを固定する。
    # 条件: host と明示ポート(6543)を含む URL を渡す。
    # 期待値: host=localhost, port=6543 が返る。
    assert _host_port_from_url("postgresql://localhost:6543/app", 5432) == (
        "localhost",
        6543,
    )


def test_host_port_from_url_uses_default_port_when_not_present() -> None:
    # 目的: URL にポートがない場合のデフォルト適用ルールを固定する。
    # 条件: ポート未指定 URL と default_port=5432 を渡す。
    # 期待値: host=localhost, port=5432 が返る。
    assert _host_port_from_url("postgresql://localhost/app", 5432) == (
        "localhost",
        5432,
    )


def test_host_port_from_url_returns_none_on_missing_host() -> None:
    # 目的: ホスト欠落 URL を不正入力として扱う挙動を固定する。
    # 条件: host が空の URL を渡す。
    # 期待値: None を返す。
    assert _host_port_from_url("postgresql:///app", 5432) is None


def test_host_port_from_url_returns_none_on_invalid_port() -> None:
    # 目的: 範囲外ポートを不正入力として扱う挙動を固定する。
    # 条件: 65535 を超えるポート(99999)を含む URL を渡す。
    # 期待値: None を返す。
    assert _host_port_from_url("postgresql://localhost:99999/app", 5432) is None


def test_host_port_from_url_uses_mssql_default_port() -> None:
    # 目的: Azure SQL 用 URL でポート未指定時の既定値(1433)適用を固定する。
    # 条件: mssql URL と default_port=1433 を渡す。
    # 期待値: host=localhost, port=1433 が返る。
    assert (
        _host_port_from_url(
            "mssql+pyodbc://@localhost/app?driver=ODBC+Driver+18+for+SQL+Server",
            1433,
        )
        == ("localhost", 1433)
    )
