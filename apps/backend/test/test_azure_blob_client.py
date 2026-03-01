from __future__ import annotations

import sys
from types import ModuleType

from app.adapters.storage import azure_blob


def test_create_blob_service_client_uses_connection_string(monkeypatch) -> None:
    # 目的: Blob 接続文字列有効時に from_connection_string 経由で client が生成されることを保証する。
    # 条件: AZURE_BLOB_USE_CONNECTION_STRING=true 相当の settings を差し込む。
    # 期待値: conn_str がそのまま渡される。
    settings = type(
        "Settings",
        (),
        {
            "azure_blob_use_connection_string": True,
            "azure_blob_connection_string": "UseDevelopmentStorage=true;",
            "azure_blob_account_url": None,
        },
    )()
    captured: dict[str, object] = {}

    class _FakeBlobServiceClient:
        @staticmethod
        def from_connection_string(conn_str: str):
            captured["conn_str"] = conn_str
            return "connection-string-client"

    fake_module = ModuleType("azure.storage.blob")
    fake_module.BlobServiceClient = _FakeBlobServiceClient

    azure_blob._create_blob_service_client.cache_clear()
    monkeypatch.setattr(azure_blob, "get_settings", lambda: settings)
    monkeypatch.setitem(sys.modules, "azure.storage.blob", fake_module)

    result = azure_blob._create_blob_service_client()

    assert result == "connection-string-client"
    assert captured["conn_str"] == "UseDevelopmentStorage=true;"


def test_create_blob_service_client_uses_default_credential(monkeypatch) -> None:
    # 目的: 接続文字列未使用時に account_url + DefaultAzureCredential で client が生成されることを保証する。
    # 条件: AZURE_BLOB_USE_CONNECTION_STRING=false 相当の settings を差し込む。
    # 期待値: account_url と credential が constructor に渡る。
    settings = type(
        "Settings",
        (),
        {
            "azure_blob_use_connection_string": False,
            "azure_blob_connection_string": None,
            "azure_blob_account_url": "https://unit-test.blob.core.windows.net/",
        },
    )()
    captured: dict[str, object] = {}
    sentinel_credential = object()

    class _FakeBlobServiceClient:
        def __init__(self, *, account_url: str, credential: object):
            captured["account_url"] = account_url
            captured["credential"] = credential

    fake_module = ModuleType("azure.storage.blob")
    fake_module.BlobServiceClient = _FakeBlobServiceClient

    azure_blob._create_blob_service_client.cache_clear()
    monkeypatch.setattr(azure_blob, "get_settings", lambda: settings)
    monkeypatch.setattr(azure_blob, "_get_default_credential", lambda: sentinel_credential)
    monkeypatch.setitem(sys.modules, "azure.storage.blob", fake_module)

    result = azure_blob._create_blob_service_client()

    assert isinstance(result, _FakeBlobServiceClient)
    assert captured["account_url"] == "https://unit-test.blob.core.windows.net"
    assert captured["credential"] is sentinel_credential
