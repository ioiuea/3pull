# Docker Init Script

このディレクトリの `deploy.sh` は `infra/main.sh` 実行時に自動生成されます。

## 目的

- メンテナンス VM から ACR への `az acr login`
- Docker image の `buildx` build
- Docker image の ACR push
- build / push 結果の確認

## 使い方

実行時に必要なのは以下の 4 つです。

- `IMAGE_TAG`
- `VITE_BACKEND_BASE_URL`
- `VITE_PRODUCT_NAME`
- `VITE_ENABLE_EMAIL_AUTH`

例:

```bash
IMAGE_TAG="$(git rev-parse --short HEAD)" \
VITE_BACKEND_BASE_URL="https://api.example.com" \
VITE_PRODUCT_NAME="sample-system" \
VITE_ENABLE_EMAIL_AUTH="true" \
./scripts/init/docker/deploy.sh
```

補足:

- `deploy.sh` は `infra/main.sh` 再実行時に上書きされます。
- 手動編集は推奨しません。変更が必要な場合は `infra/main.sh` / `infra/lib/post-actions.sh` 側を修正してください。
- 実行前に `az login --identity --client-id <ACR_ADMIN_MANAGED_IDENTITY_CLIENT_ID>` を済ませておく前提です。
