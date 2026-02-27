"""
ストレージ接続アダプターパッケージ.

- Azure Blob への入出力を扱う
"""

from app.adapters.storage.azure_blob import (
    delete_blob,
    download_blob_bytes,
    upload_bytes,
)

__all__ = [
    "delete_blob",
    "download_blob_bytes",
    "upload_bytes",
]
