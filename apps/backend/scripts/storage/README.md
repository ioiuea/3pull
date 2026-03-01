# Azure Blob Storage 初期化

このディレクトリには、Azure Blob Storage の初期構築スクリプトがあります。

現時点では、非同期ジョブ成果物の保存先コンテナを作成するためのスクリプトを配置しています。

## 対象

- `AZURE_BLOB_CONTAINER` で指定したコンテナ

## 前提

- `apps/backend/.env` または環境変数で以下が設定されていること
- `AZURE_BLOB_ACCOUNT_URL`
- `AZURE_BLOB_CONTAINER`
- `AZURE_BLOB_USE_CONNECTION_STRING`
- 必要時のみ `AZURE_BLOB_CONNECTION_STRING`

既定では `AZURE_BLOB_USE_CONNECTION_STRING=false` とし、`az login + DefaultAzureCredential` で接続します。
ローカルで接続文字列フォールバックを使う場合のみ、`AZURE_BLOB_USE_CONNECTION_STRING=true` にして `AZURE_BLOB_CONNECTION_STRING` を設定してください。

## ファイル構成

- `apps/backend/scripts/storage/create_blob_container.py`
  - Azure Blob に接続し、コンテナが存在しなければ作成します。
  - 既に存在する場合は成功扱いで終了します。

## 実行方法

```bash
uv --directory apps/backend run python scripts/storage/create_blob_container.py
```

## 実行結果

- コンテナ未作成: 作成して成功
- コンテナ作成済み: 何も変更せず成功

初期構築時に再実行しても安全な、冪等実行を前提にしています。
