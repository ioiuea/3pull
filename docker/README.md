# Docker

`docker/` 配下には、backend / frontend のローカル検証用コンテナ定義を置きます。

- [api.Dockerfile](/Users/hiroki.ueda/Dev/3pull/docker/api.Dockerfile)
  - FastAPI を `gunicorn + uvicorn worker` で起動する API 用イメージ
- [worker.Dockerfile](/Users/hiroki.ueda/Dev/3pull/docker/worker.Dockerfile)
  - `WORKER_MODULE` で対象ジョブを切り替える常駐 worker 用イメージ
- [cleanup.Dockerfile](/Users/hiroki.ueda/Dev/3pull/docker/cleanup.Dockerfile)
  - `CLEANUP_COMMAND` で対象 cleanup を切り替える都度実行型イメージ
- [web.Dockerfile](/Users/hiroki.ueda/Dev/3pull/docker/web.Dockerfile)
  - frontend の静的成果物を `nginx` で配信する web 用イメージ
- [frontend-nginx.conf](/Users/hiroki.ueda/Dev/3pull/docker/frontend-nginx.conf)
  - SPA のパスを `/index.html` にフォールバックする `nginx` 設定

## Build

プロジェクトルートを build context にして、各イメージを個別にビルドします。

Makefile を使う場合は、まとめて次で実行できます。

```bash
make docker-build
```

個別 build は次です。

```bash
docker build -f docker/api.Dockerfile -t 3pull-api:local .
docker build -f docker/worker.Dockerfile -t 3pull-worker:local .
docker build -f docker/cleanup.Dockerfile -t 3pull-cleanup:local .
docker build -f docker/web.Dockerfile -t 3pull-web:local .
```

## Run

### API

API は `apps/backend/.env` を読み込み、`8000` で待ち受けます。

Makefile を使う場合:

```bash
make docker-run-api
```

```bash
docker run --rm --init -p 8000:8000 --env-file apps/backend/.env 3pull-api:local
```

ホスト側の `8000` が埋まっている場合は、左側だけ変更します。

```bash
docker run --rm --init -p 8001:8000 --env-file apps/backend/.env 3pull-api:local
```

### Worker

worker は常駐型です。`WORKER_MODULE` で監視対象のキューを切り替えます。

Makefile を使う場合:

```bash
make docker-run-worker-auth-audit-export
```

```bash
make docker-run-worker-sample-wait-blob
```

```bash
docker run --rm --init --env-file apps/backend/.env \
  -e WORKER_MODULE=app.workers.entrypoints.auth_audit_export \
  3pull-worker:local
```

```bash
docker run --rm --init --env-file apps/backend/.env \
  -e WORKER_MODULE=app.workers.entrypoints.sample_wait_blob \
  3pull-worker:local
```

### Cleanup

cleanup は 1 回だけ実行して終了します。`CLEANUP_COMMAND` で対象を切り替えます。

Makefile を使う場合:

```bash
make docker-run-cleanup-sessions
```

```bash
make docker-run-cleanup-audit
```

```bash
make docker-run-cleanup-jobs-dry-run
```

```bash
docker run --rm --init --env-file apps/backend/.env \
  -e CLEANUP_COMMAND=sessions \
  3pull-cleanup:local
```

```bash
docker run --rm --init --env-file apps/backend/.env \
  -e CLEANUP_COMMAND=audit \
  3pull-cleanup:local
```

```bash
docker run --rm --init --env-file apps/backend/.env \
  -e CLEANUP_COMMAND="jobs --dry-run" \
  3pull-cleanup:local
```

### Web

web はコンテナ内で `3000` を使います。ローカルでも `3000` で合わせる場合はそのまま公開します。

Makefile を使う場合:

```bash
make docker-run-web
```

```bash
docker run --rm -p 3000:3000 3pull-web:local
```

## Authentication Notes

Docker コンテナ内では、ホストの `az login` 状態はそのまま使えません。

- backend API
  - 起動自体はできますが、Azure リソースへ接続するエンドポイントでは認証設定が必要です
- worker / cleanup
  - `DefaultAzureCredential` を使う処理は、そのままではコンテナ内で失敗しやすいです

ローカル Docker 検証では、以下のいずれかで認証を与えます。

1. 接続文字列を使う
- `SERVICE_BUS_USE_CONNECTION_STRING=true`
- `SERVICE_BUS_CONNECTION_STRING=...`
- `AZURE_BLOB_USE_CONNECTION_STRING=true`
- `AZURE_BLOB_CONNECTION_STRING=...`

2. `EnvironmentCredential` を使う
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

注意:

- Storage Account で `Key based authentication` を禁止している場合、Blob の接続文字列認証は `403 KeyBasedAuthenticationNotPermitted` になります
- 本番の AKS では、Docker 単体起動とは異なり `Workload Identity` を前提にします

## Verification Hints

- API
  - 起動後に `http://localhost:8000/backend/health` を確認する
  - 停止時のシグナル伝播を安定させるため、`docker run` には `--init` を付ける
- Web
  - `http://localhost:3000` で配信確認
- Worker
  - `worker.loop.started` が出ることを確認する
  - サンプルジョブ投入時に `worker.message.completed` まで進むかを確認する
- Cleanup
  - `jobs --dry-run` で安全に起動確認する
