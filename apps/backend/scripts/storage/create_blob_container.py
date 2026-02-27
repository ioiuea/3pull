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

# `uv run python scripts/storage/create_blob_container.py` で直接実行しても
# backend ルート配下の `app` パッケージを import できるようにする。
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.settings import get_settings


def _create_blob_service_client() -> Any:
    """Storage 接続文字列から BlobServiceClient を生成する。"""
    settings = get_settings()

    credential = settings.azure_blob_credential
    if not isinstance(credential, str) or "AccountKey=" not in credential:
        raise RuntimeError(
            "AZURE_BLOB_CREDENTIAL must be a Storage connection string containing "
            "AccountKey="
        )

    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient.from_connection_string(credential)


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
