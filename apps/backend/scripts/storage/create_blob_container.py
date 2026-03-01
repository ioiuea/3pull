"""
Azure Blob Storage のコンテナを初期化する CLI。

- `.env` / 環境変数から接続情報を取得する
- 対象コンテナが無ければ作成する
- 既に存在する場合は成功扱いにする
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential

# `uv run python scripts/storage/create_blob_container.py` で直接実行しても
# backend ルート配下の `app` パッケージを import できるようにする。
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.settings import get_settings


def _create_blob_service_client() -> Any:
    """BlobServiceClient を生成する。"""
    settings = get_settings()

    from azure.storage.blob import BlobServiceClient

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

    return BlobServiceClient(
        account_url=account_url.rstrip("/"),
        credential=DefaultAzureCredential(),
    )


def main() -> None:
    """コンテナが存在しなければ作成する。"""
    settings = get_settings()
    service = _create_blob_service_client()
    container_name = settings.azure_blob_container
    container_client = service.get_container_client(container_name)

    try:
        container_client.create_container()
    except Exception as exc:  # pragma: no cover
        if exc.__class__.__name__ == "ResourceExistsError":
            print(f"[ok] Blob container already exists: {container_name}")
            return
        raise

    print(f"[ok] Blob container created: {container_name}")


if __name__ == "__main__":
    main()
