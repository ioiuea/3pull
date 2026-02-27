# pyright: reportMissingImports=false

"""
Azure Blob Storage アダプタ.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def _create_blob_service_client() -> Any:
    """
    BlobServiceClient を生成する.
    """
    settings = get_settings()
    from azure.storage.blob import BlobServiceClient

    credential: Any = settings.azure_blob_credential

    if not isinstance(credential, str) or "AccountKey=" not in credential:
        raise RuntimeError(
            "AZURE_BLOB_CREDENTIAL must be a Storage connection string containing "
            "AccountKey="
        )
    return BlobServiceClient.from_connection_string(credential)


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
    blob_client = client.get_blob_client(
        container=settings.azure_blob_container,
        blob=blob_path,
    )
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
