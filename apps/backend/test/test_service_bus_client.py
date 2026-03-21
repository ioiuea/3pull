from __future__ import annotations

from app.adapters.queue import service_bus_client


def test_create_service_bus_client_uses_connection_string(monkeypatch) -> None:
    # 目的: 接続文字列有効時に from_connection_string 経由で client が生成されることを保証する。
    # 条件: SERVICE_BUS_USE_CONNECTION_STRING=true 相当の settings を差し込む。
    # 期待値: conn_str がそのまま渡される。
    settings = type(
        "Settings",
        (),
        {
            "service_bus_use_connection_string": True,
            "service_bus_connection_string": "Endpoint=sb://unit-test.servicebus.windows.net/;",
            "service_bus_namespace_fqdn": None,
        },
    )()
    captured: dict[str, object] = {}

    def _fake_from_connection_string(*, conn_str: str):
        captured["conn_str"] = conn_str
        return "connection-string-client"

    # 接続方式の分岐だけを検証したいため、
    # settings は connection string 有効のテスト用設定へ差し替える。
    monkeypatch.setattr(service_bus_client, "get_settings", lambda: settings)
    # Service Bus SDK 本体を呼ばずに引数だけ確認したいため、
    # from_connection_string を fake 実装へ差し替える。
    monkeypatch.setattr(
        service_bus_client.ServiceBusClient,
        "from_connection_string",
        _fake_from_connection_string,
    )

    result = service_bus_client._create_service_bus_client()

    assert result == "connection-string-client"
    assert captured["conn_str"] == "Endpoint=sb://unit-test.servicebus.windows.net/;"


def test_create_service_bus_client_uses_default_credential(monkeypatch) -> None:
    # 目的: 接続文字列未使用時に FQDN + DefaultAzureCredential で client が生成されることを保証する。
    # 条件: SERVICE_BUS_USE_CONNECTION_STRING=false 相当の settings を差し込む。
    # 期待値: fully_qualified_namespace と credential が constructor に渡る。
    settings = type(
        "Settings",
        (),
        {
            "service_bus_use_connection_string": False,
            "service_bus_connection_string": None,
            "service_bus_namespace_fqdn": "unit-test.servicebus.windows.net",
        },
    )()
    captured: dict[str, object] = {}
    sentinel_credential = object()

    class _FakeServiceBusClient:
        def __init__(self, *, fully_qualified_namespace: str, credential: object):
            captured["fully_qualified_namespace"] = fully_qualified_namespace
            captured["credential"] = credential

    # FQDN + credential 分岐だけを検証したいため、
    # settings は接続文字列未使用のテスト用設定へ差し替える。
    monkeypatch.setattr(service_bus_client, "get_settings", lambda: settings)
    # 実際の credential 生成を避けるため、
    # default credential 取得関数を sentinel を返す fake へ差し替える。
    monkeypatch.setattr(
        service_bus_client,
        "_get_default_credential",
        lambda: sentinel_credential,
    )
    # SDK 実装への依存を避け、
    # constructor 引数だけを確認するため ServiceBusClient を fake 化する。
    monkeypatch.setattr(service_bus_client, "ServiceBusClient", _FakeServiceBusClient)

    result = service_bus_client._create_service_bus_client()

    assert isinstance(result, _FakeServiceBusClient)
    assert captured["fully_qualified_namespace"] == "unit-test.servicebus.windows.net"
    assert captured["credential"] is sentinel_credential
