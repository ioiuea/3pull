# workers

`app.workers` は、キューから受け取った非同期ジョブを実行するパッケージです。

この層の責務は、Service Bus などから受信したメッセージを解釈し、対応する job handler を呼び出して、ジョブの進行・完了・失敗を処理することです。

## この層に置くもの

- worker 実行ループ
- job type と handler の対応付け
- worker 起動用 entrypoint
- 非同期ジョブ本体の実行処理
- queue メッセージの schema

## この層に置かないもの

- HTTP endpoint
- 定期実行 scheduler
- DB model 定義
- 外部接続 client の低レベル実装

`workers` はメッセージ起点で動く実行層です。ジョブ投入自体は `api` や `services/jobs` 側で行い、ここでは投入済みジョブを実行します。

## 構成

- `runtime.py`
  - 共通 worker 実行ループ
- `job_registry.py`
  - `job_type` と実行関数の対応表
- `entrypoints/`
  - job type ごとの worker 起動モジュール
- `jobs/`
  - 非同期ジョブ本体の実装
- `messages/`
  - queue で受け渡すメッセージ schema

## 利用方針

worker は通常、entrypoint から起動します。

```bash
python -m app.workers.entrypoints.auth_audit_export
python -m app.workers.entrypoints.sample_wait_blob
```

コード上では `runtime` がメッセージを受け取り、`job_registry` を使って handler を解決し、`jobs/` 配下の実処理を呼び出します。

## schedulers との違い

- `workers`
  - キューから届くメッセージ起点で実行する
  - 非同期ジョブの本体処理を担当する
- `schedulers`
  - 時間起点で実行する
  - cleanup などの定期運用処理を担当する

## 関連 package

- `app.services.jobs`
  - worker が実行するジョブを事前に投入する層
- `app.adapters.queue`
  - queue 送受信
- `app.adapters.storage`
  - ジョブ成果物の保存先
- `app.repositories.jobs`
  - ジョブ状態の永続化 access
