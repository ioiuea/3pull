# Backend タスク整理

## 1. このドキュメントの位置づけ

- 本ドキュメントは、backend 側で進めてきた設計メモ・作業メモを、`現状の実装` を正として統合整理したものです。
- 古いメモに残っていた過去時点の案や途中状態は、そのまま写さず、現在のコードベースと整合する形に再整理しています。
- 目的は次の 3 つです。
  - 現在の backend 要件・仕様を 1 ファイルで確認できるようにする
  - 完了済み作業と未完了作業を明確に分ける
  - 今後の Docker / Helm / AKS 反映を進めるための実装基準を固定する

## 2. スコープ

- 本ドキュメントは、backend の以下 2 系統の作業を対象にします。
  - 認証セッション運用改善
    - `sessions` cleanup
    - `auth_audit_logs` の保持・retention cleanup
  - 非同期ジョブ基盤
    - `Azure Service Bus + 専用 worker`
    - `async_jobs` / `async_job_artifacts`
    - `Azure Blob Storage` 成果物保存

## 3. 現在の前提

### 3.1 実行環境前提

- backend は `FastAPI + SQLAlchemy + Alembic + PostgreSQL` を前提とする。
- 本番実行環境は `AKS` を前提とする。
- cleanup は API リクエスト経路ではなく、CLI 実行を前提にする。
- 非同期ジョブ worker は API とは別プロセスで実行する。

### 3.2 認証・資格情報前提

- 本番では、Service Bus / Blob Storage ともに `Microsoft Entra Workload Identity` を前提とする。
- ローカル開発では、Service Bus / Blob Storage ともに `az login + DefaultAzureCredential` を標準とする。
- 接続文字列はローカル検証用の例外的フォールバックであり、常用しない。

### 3.3 現在の未実装範囲

- `Dockerfile`
- `Helm chart`
- `KEDA ScaledObject`
- `AKS Workload Identity` の manifest / values 化

補足:

- リポジトリ上で `Dockerfile`、`Chart.yaml`、`values*.yaml` は現時点で未作成です。
- したがって、これらは「要件に含まれているが未着手」の扱いです。

## 4. 要件・仕様（現行）

### 4.1 認証セッション運用

- `sessions` は認証制御用の短期データとして扱う。
- セッションの自然失効は `expires_at` で管理する。
- 明示失効は `revoked_at` で管理する。
- cleanup では、`expires_at` が cutoff を過ぎたセッションを段階削除する。
- 削除対象は「期限切れ直後」ではなく、`grace days` を超えたものに限定する。

現在の設定方針:

- `SESSION_TTL_HOURS`
- `SESSION_EXPIRED_GRACE_DAYS`
- `SESSION_CLEANUP_ENABLED`
- `CLEANUP_BATCH_SIZE`

### 4.2 認証監査ログ

- 監査ログは `auth_audit_logs` に記録する。
- `auth_audit_logs` は月次パーティションで運用する。
- 保持期間を超えた古い月次パーティションは cleanup で drop する。
- 監査ログ記録はベストエフォートとし、記録失敗が本処理を失敗させない。
- `metadata` は allowlist + サイズ制限前提で扱う。

現在の設定方針:

- `AUTH_AUDIT_RETENTION_MONTHS`
- `AUDIT_CLEANUP_ENABLED`

#### 4.2.1 監査ログ記録の詳細ルール

- `event_type` は `AuthAuditEventType`（ENUM）を使用する。
- `user_id` / `session_id` は「取得できる場合のみ」保存する。
- 監査ログ記録失敗は本来の認証処理を失敗させない。
- `metadata` は allowlist 前提で扱い、DB 側では 4KB 制限を持つ。
- `metadata` の 4KB 制限は、`auth_audit_logs` テーブルの DB 制約で担保する。
- `metadata` には、平文トークンや平文パスワードなどの機密情報を保存しない。

現在の `AuthAuditEventType` 一覧:

- `auth.login.success`
- `auth.login.fail`
- `auth.logout.success`
- `auth.logout.fail`
- `auth.session_refresh.success`
- `auth.session_refresh.fail`
- `auth.session_revoke.success`
- `auth.session_revoke.fail`
- `auth.signup.success`
- `auth.signup.fail`
- `auth.email_verify.success`
- `auth.email_verify.fail`
- `auth.password_change.success`
- `auth.password_change.fail`
- `auth.password_reset_request.success`
- `auth.password_reset_request.fail`
- `auth.password_reset_confirm.success`
- `auth.password_reset_confirm.fail`
- `auth.entra_callback.success`
- `auth.entra_callback.fail`
- `auth.entra_profile_fetch.success`
- `auth.entra_profile_fetch.fail`

#### 4.2.2 IP 記録ルール

- `client_ip`
  - `X-Forwarded-For` の先頭 IP を優先する。
  - `X-Forwarded-For` が無い、または先頭が不正な場合は `connection_ip` を使う。
- `xff_raw`
  - `X-Forwarded-For` の生値を保存する。
  - 空文字は `None` とする。
- `connection_ip`
  - `request.client.host` を IP 正規化して保存する。

参照実装:

- `apps/backend/app/core/security/client_ip.py`
- `apps/backend/app/api/routers/auth.py::_record_auth_audit`

ローカル検証時の補足:

- ローカル開発では `X-Forwarded-For` が付かないことが多いため、通常は `client_ip` に `connection_ip` がそのまま入る。
- この場合、`xff_raw` は `None` になる。

#### 4.2.3 イベント別の `user_id` / `session_id` 保存方針

正常系:

| event_type | user_id | session_id | 現在の実装方針 |
|---|---|---|---|
| `auth.signup.success` | あり | なし | ユーザー作成後、セッション未発行 |
| `auth.email_verify.success` | あり | なし | 検証トークン消費後にユーザー確定 |
| `auth.login.success` | あり | あり | セッション発行後に新セッション ID を記録 |
| `auth.password_change.success` | あり | あり | 現在の有効セッション ID を記録 |
| `auth.password_reset_request.success` | 条件付き | なし | 対象ユーザーが存在する場合のみ `user_id` を記録 |
| `auth.password_reset_confirm.success` | あり | なし | リセット対象ユーザーを記録 |
| `auth.entra_callback.success` | あり | あり | Entra ログイン成功後に発行したセッション ID を記録 |
| `auth.entra_profile_fetch.success` | あり | あり | 現在セッションを解決して記録 |
| `auth.session_revoke.success` | 条件付き | 条件付き | logout 時に有効セッションを解決できた場合のみ記録 |
| `auth.logout.success` | 条件付き | 条件付き | revoke 時に解決できた値を引き継いで記録 |
| `auth.session_refresh.success` | あり | あり | refresh 後の新セッション ID を記録 |

異常系:

| event_type | user_id | session_id | 現在の実装方針 |
|---|---|---|---|
| `auth.signup.fail` | なし | なし | ユーザー作成前失敗 |
| `auth.email_verify.fail` | 条件付き | なし | 監査用のベストエフォート解決で `user_id` を付ける |
| `auth.login.fail` | なし | なし | 認証失敗時は主体未確定 |
| `auth.password_change.fail` | あり | あり | ログイン済みかつ有効セッション解決済み |
| `auth.password_reset_confirm.fail` | 条件付き | なし | 監査用のベストエフォート解決で `user_id` を付ける |
| `auth.entra_callback.fail` | なし | なし | ユーザー / セッション確定前失敗 |
| `auth.entra_profile_fetch.fail` | あり（多く） | 条件付き | 分岐時点でセッション解決済みなら `session_id` も記録 |
| `auth.session_revoke.fail` | 条件付き | 条件付き | 事前に有効セッションを解決できた場合のみ記録 |
| `auth.session_refresh.fail` | 条件付き | 条件付き | 事前に有効セッションを解決できた場合のみ記録 |

補足:

- `AuthAuditEventType` には `auth.logout.fail`、`auth.password_reset_request.fail` も定義されている。
- ただし、現在の `apps/backend/app/api/routers/auth.py` では、これらのイベントは記録していない。

#### 4.2.4 監査用ベストエフォート解決

- 失敗系でも主体特定率を上げるため、監査専用の解決関数を使う。
- 解決できない場合は例外を送出せず、`None` を返す。
- 本来の認証判定やレスポンスには影響させない。

現在の実装:

- `resolve_email_verify_user_id_for_audit(token)`
  - `email_verification_tokens` から `identity` をたどって `user_id` を解決する
- `resolve_password_reset_user_id_for_audit(token)`
  - `password_reset_tokens` から `identity` をたどって `user_id` を解決する

### 4.3 非同期ジョブ基盤

- 非同期ジョブ基盤は `Azure Service Bus + 専用 worker` を標準とする。
- ジョブ状態の正本は `async_jobs` テーブルとする。
- 成果物メタデータの正本は `async_job_artifacts` テーブルとする。
- 成果物本体は `Azure Blob Storage` に保存する。
- API サーバは `ジョブ作成 + queue への投入` を担当する。
- worker は `queue から受信 + ジョブ実行 + 状態更新` を担当する。

### 4.4 Service Bus メッセージ方針

- メッセージは `job_id` 中心の最小構成とする。
- worker は `job_id` を使って `async_jobs` から詳細を取得する。
- メッセージには、少なくとも以下を載せる。
  - `job_id`
  - `job_type`
  - `task_name`
  - `requested_at`（トレース用途）

### 4.5 キュー構成

- キューは `job_type` ごとに分ける。
- 現在の標準 queue 名:
  - `auth-audit-export`
  - `sample-wait-blob`

### 4.6 worker 構成

- worker は共通 runtime を持ち、ジョブ種別ごとの差分は job 実装と起動スクリプトで分ける。
- worker は `1 Pod / 1メッセージ直列処理` を前提とする。
- 受信モードは `peek-lock` を前提とする。

### 4.7 同時実行制御

- 同時実行制御は `job_type` 単位で判定する。
- `queued` / `running` を「枠消費中」として扱う。
- 全体上限とユーザー上限は、同じ `job_type` のアクティブジョブのみを対象に数える。

現在の設定方針:

- `ASYNC_JOB_GLOBAL_CONCURRENCY`
- `ASYNC_JOB_PER_USER_CONCURRENCY`

### 4.8 状態遷移・失敗処理

- 状態は以下を維持する。
  - `queued`
  - `running`
  - `succeeded`
  - `failed`
  - `canceled`
  - `expired`
- worker は開始時に `queued -> running` を条件付き更新で claim し、二重実行を避ける。
- 終了済みジョブは no-op 扱いで再実行しない。
- キャンセルは queue 上のメッセージ削除ではなく、`DB status = canceled` で表現する。

### 4.9 retry / DLQ

- 初期段階では、retry は Service Bus の再配送を主に使う。
- 一時失敗時は `abandon`。
- 恒久失敗時は `dead-letter`。
- `DLQ` 到達時は自動再投入せず、手動調査・手動再実行とする。
- 初期 `maxDeliveryCount` は `5`。

### 4.10 遅延実行

- 遅延実行（旧 countdown 相当）は初期スコープ外。
- 即時実行ジョブのみを正式サポートする。

### 4.11 stuck ジョブ対応

- `running` のまま一定時間を超えたジョブは cleanup で `failed` 化する。
- 自動で `queued` に戻して再実行はしない。
- stuck 判定の初期値は `45分`（`2700秒`）。

現在の設定方針:

- `ASYNC_JOB_RUNNING_TIMEOUT_SECONDS`

## 5. 現在の実装状態

### 5.1 認証セッション / 監査ログ

実装済み:

- `sessions` cleanup CLI が存在する。
- `auth_audit_logs` retention cleanup CLI が存在する。
- cleanup 共通入口は `apps/backend/app/schedulers/cleanup/runner_registry.py` に統合済み。
- cleanup 実体は以下に分離済み。
  - `apps/backend/app/schedulers/cleanup/runners/sessions.py`
  - `apps/backend/app/schedulers/cleanup/runners/audit_logs.py`
  - `apps/backend/app/schedulers/cleanup/runners/async_jobs.py`
- cleanup 共通ヘルパーは `apps/backend/app/schedulers/cleanup/helpers.py`。
- `apps/backend/app/schedulers/scheduler_cleanup.py` から CLI 実行可能。

現在の cleanup コマンド責務:

- `sessions`
  - 期限切れ + grace 超過のセッションを batch 削除
- `audit`
  - retention 超過の監査ログ月次パーティションを drop
  - 次月パーティションを先行作成
- `jobs`
  - 期限切れ成果物 cleanup
  - stuck `running` ジョブの `failed` 化

### 5.2 非同期ジョブ

実装済み:

- queue adapter
  - `apps/backend/app/adapters/queue/service_bus_client.py`
  - `apps/backend/app/adapters/queue/message_sender.py`
- ジョブ投入サービス
  - `apps/backend/app/services/jobs/async_job_dispatcher.py`
- jobs API
  - `apps/backend/app/api/routers/jobs/helpers.py`
  - `apps/backend/app/api/routers/jobs/query.py`
  - `apps/backend/app/api/routers/jobs/commands.py`
  - `apps/backend/app/api/routers/jobs/create/`
- worker 共通部
  - `apps/backend/app/workers/runtime.py`
  - `apps/backend/app/workers/job_registry.py`
  - `apps/backend/app/workers/messages/async_job.py`
- worker ジョブ本体
  - `apps/backend/app/workers/jobs/audit_export.py`
  - `apps/backend/app/workers/jobs/sample_wait_blob.py`
- worker 起動スクリプト
  - `apps/backend/app/workers/entrypoints/auth_audit_export.py`
  - `apps/backend/app/workers/entrypoints/sample_wait_blob.py`
- cleanup 連携
  - `apps/backend/app/schedulers/cleanup/runners/async_jobs.py`

実装済みの認証方針:

- Service Bus:
  - 標準は `DefaultAzureCredential`
  - 接続文字列はフォールバック
- Blob Storage:
  - 標準は `DefaultAzureCredential`
  - 接続文字列はフォールバック

実装済みの設定系:

- 非同期ジョブの業務設定は `ASYNC_JOB_*`
- Service Bus は `SERVICE_BUS_*`
- Blob Storage は `AZURE_BLOB_*`

### 5.3 Frontend 連携（backend 観点）

実装済み:

- frontend は backend API 契約を維持したまま動作する前提。
- グローバルジョブ集約は frontend 側で `useGlobalAsyncJobs()` に統一されている。
- 個別ページでは `SWR` による 5 秒ポーリングを利用している。
- 非同期ジョブサンプルページには、ポーリング由来の表示ラグ説明を反映済み。

## 6. これまでの作業ステップと進捗

### Step 0. 仕様固定

進捗: 完了

- セッション TTL / grace / cleanup batch の基本方針を確定
- 監査ログ retention 方針を確定
- 監査ログのイベント記録・PII 境界の基本方針を確定
- 非同期ジョブの queue 命名規則を `<job-type>` に固定
- 初期 queue 名を `auth-audit-export` / `sample-wait-blob` に固定
- `KEDA` 初期値を `minReplicaCount=0`, `maxReplicaCount=3` に固定
- `maxDeliveryCount=5`
- `DLQ` は手動調査・手動再実行
- stuck 判定を `45分` に固定

### Step 1. DB スキーマと設定の整理

進捗: 完了

- `auth_audit_logs` の導入を前提とする実装がコードに反映済み
- 月次パーティション前提の cleanup 実装が存在
- 非同期ジョブ設定を `ASYNC_JOB_*` / `SERVICE_BUS_*` / `AZURE_BLOB_*` に整理済み
- Service Bus / Blob の `DefaultAzureCredential` 前提を設定へ反映済み

### Step 2. アプリケーション実装（認証・cleanup・非同期ジョブ）

進捗: 完了

- 認証監査ログ記録を実装済み
- `SESSION_TTL_HOURS` を起点にしたセッション運用へ整理済み
- cleanup CLI（`sessions` / `audit` / `jobs`）を実装済み
- 非同期ジョブの queue adapter / dispatcher を実装済み
  - `service_bus_client.py`
  - `message_sender.py`
  - `async_job_dispatcher.py`
- 非同期ジョブ本体を `app/workers/jobs/` に集約済み
- worker 共通 runtime を実装済み
  - `runtime.py`
  - `job_registry.py`
  - `messages/async_job.py`
  - `entrypoints/`
- jobs API を `helpers.py` / `query.py` / `commands.py` / `create/` に整理済み
- create API は DB commit 後 enqueue へ修正済み
- `jobs` cleanup を 2 フェーズ化済み
  - artifact cleanup
  - stale `running` fail 化
- `claim_queued_job_for_run()` による原子的 claim を実装済み
- `job_type` 単位の同時実行制御へ修正済み
- Blob Storage も `DefaultAzureCredential` 前提へ移行済み

### Step 3. Migration 整理

進捗: 完了

- 今回の async jobs 変更では追加 migration は不要と整理済み
- 既存 ORM / Alembic と今回のロジック変更に不整合がないことを確認済み

### Step 4. 開発導線とローカル整合

進捗: 完了

- `make up-worker`
- `make dev-worker`
- 個別 `make up-worker-*`
- 個別 `make dev-worker-*`

は `python -m app.workers.entrypoints.<job>` 前提に更新済み

- frontend API 契約は維持
- サンプルページのポーリング説明まで反映済み
- Service Bus client / message sender / worker runtime / jobs API ヘルパーなどのテストを新構成に合わせて更新済み

### Step 5. ドキュメント更新

進捗: 完了

- `apps/backend/README.md`
- `apps/frontend/README.md`

### Step 6. コンテナ化

進捗: 完了

完了:

- `docker/api.Dockerfile` を追加
- `docker/worker.Dockerfile` を追加
- `docker/schedulers.Dockerfile` を追加
- `docker/web.Dockerfile` を追加
- `docker/frontend-nginx.conf` を追加
- `.dockerignore` を追加
- `docker/README.md` を作成し、build / run 手順を整理
- `Makefile` に Docker build / run ターゲットを追加
- `api / worker / schedulers / web` の build を確認
- `api / worker / schedulers / web` の最低限の起動確認を実施
- `api / worker / schedulers` の `CMD` を `exec` 化し、`--init` 前提で停止しやすい形に調整

未完:

- Helm / CI から呼ぶ build 手順の確定
- CI 上でのコンテナ build 検証の自動化

- AKS / Helm / KEDA 以降の配備タスクは `docs/kubernetes-task.md` で管理する

## 8. 現時点の判断メモ

### 8.1 すでに確定しているもの

- queue は job ごとに分ける
- worker は job ごとに Deployment を分ける
- worker 実装は共通 runtime を使う
- キャンセルは DB ステータスで扱う
- retry は Service Bus 標準を優先する
- 遅延実行は初期スコープ外
- queue 名はシステム名なし
- Blob / Service Bus ともに `DefaultAzureCredential` を標準とする

### 8.2 今後の実装で変えない前提

- `/backend/jobs` API 契約は大きく崩さない
- `async_jobs` / `async_job_artifacts` を正本として維持する
- backend 経由の成果物ダウンロードを維持する
- ポーリング UI を前提にしつつ、frontend の契約は維持する

## 9. 完了条件

backend 側のこの作業が完了といえる条件は、次のとおりです。

1. cleanup（sessions / audit / jobs）がコンテナ・Helm・AKS まで一貫して動く
2. async jobs（API / queue / worker / Blob）が AKS 上で動く
3. Workload Identity で Service Bus / Blob に接続できる
4. `KEDA` により worker が queue 長に応じてスケールする
5. Docker / Helm / values / Runbook が揃う
6. README / docs が現行実装と一致している
