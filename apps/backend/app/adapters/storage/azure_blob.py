# pyright: reportMissingImports=false

"""
Azure Blob Storage アダプタ.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from azure.identity import DefaultAzureCredential

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def _get_default_credential() -> DefaultAzureCredential:
    """DefaultAzureCredential をキャッシュして返す."""
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def _create_blob_service_client() -> Any:
    """
    BlobServiceClient を生成する.
    """
    settings = get_settings()
    from azure.storage.blob import BlobServiceClient

    # ローカル切り分け用にだけ接続文字列を許可し、通常は Entra 認証へ寄せる。
    if settings.azure_blob_use_connection_string:
        connection_string = settings.azure_blob_connection_string
        if not isinstance(connection_string, str) or not connection_string.strip():
            raise RuntimeError(
                "AZURE_BLOB_CONNECTION_STRING is required when "
                "AZURE_BLOB_USE_CONNECTION_STRING=true"
            )
        return BlobServiceClient.from_connection_string(connection_string)

    account_url = settings.azure_blob_account_url
    if not isinstance(account_url, str) or not account_url.strip():
        raise RuntimeError(
            "AZURE_BLOB_ACCOUNT_URL is required when "
            "AZURE_BLOB_USE_CONNECTION_STRING=false"
        )
    # 本番の AKS では Workload Identity、ローカルでは az login を通じて認証される。
    return BlobServiceClient(
        account_url=account_url.rstrip("/"),
        credential=_get_default_credential(),
    )


def upload_bytes(
    *,
    blob_path: str,
    data: bytes,
    content_type: str = "text/csv; charset=utf-8",
) -> int:
    """
    bytes を Azure Blob へアップロードする.
    """
    from azure.storage.blob import ContentSettings

    settings = get_settings()
    client = _create_blob_service_client()
    # コンテナ名は設定で固定し、呼び出し側は blob_path だけを意識すればよいようにする。
    blob_client = client.get_blob_client(
        container=settings.azure_blob_container,
        blob=blob_path,
    )
    # overwrite=True なので、同じパスへの再実行でも冪等に上書きできる。
    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )
    return len(data)


def download_blob_bytes(*, blob_path: str) -> bytes:
    """
    Azure Blob から bytes を取得する.
    """
    settings = get_settings()
    client = _create_blob_service_client()
    # API 側はこの関数経由で Blob 本体を取得し、backend 経由で配信する。
    blob_client = client.get_blob_client(
        container=settings.azure_blob_container,
        blob=blob_path,
    )
    downloader = blob_client.download_blob()
    return bytes(downloader.readall())


def delete_blob(*, blob_path: str) -> None:
    """
    Azure Blob を削除する（存在しない場合は無視）。
    """
    settings = get_settings()
    client = _create_blob_service_client()
    # cleanup は Blob の存在有無を気にせず進めたいので、存在しない場合は成功扱いにする。
    blob_client = client.get_blob_client(
        container=settings.azure_blob_container,
        blob=blob_path,
    )
    try:
        blob_client.delete_blob()
    except Exception as exc:  # pragma: no cover
        if exc.__class__.__name__ == "ResourceNotFoundError":
            return
        raise
