# Kubernetes タスク整理

## 1. このドキュメントの位置づけ

- 本ドキュメントは、AKS / Helm / KEDA / Workload Identity / リリースに関する作業を整理するためのものです。
- backend / frontend のアプリ実装タスクから切り離し、Kubernetes 配備全体の観点で管理します。
- 未確定の内容は「判断メモ」や「参考メモ」として残し、実装が進んだ時点で要件へ昇格させます。

## 2. 対象範囲

- AKS へのデプロイ
- Helm chart
- KEDA
- Workload Identity
- Staging / 本番検証
- Runbook / リリース

対象外:

- backend アプリ実装そのもの
- frontend アプリ実装そのもの
- インフラ全体の長期検討（VNet / App Gateway / private 化の詳細）
  - これらは `docs/infra-task.md` も参照する

## 3. Step 7. Helm / AKS / KEDA

進捗: 未着手

### 3.1 着手前の前提整理

- Step 7 の目的は、まず AKS 上にアプリを載せるための manifest / Helm / 動作確認を成立させること
- この段階では、事前準備はできるだけ小さくし、原則として「パブリック通信前提」で進める
  - まずは AKS
  - ACR
  - Key Vault（必要なら Secret 管理）
  程度のシンプル構成を優先する
- 最終的にはプライベート構成へ寄せる前提だが、
  - VNet
  - private endpoint
  - App Gateway / AGIC
  - UDR
  などは後続フェーズで追加・再設計する
- `docs/infra-task.md` にあるネットワーク / App Gateway の検討は、
  Step 7 の Helm 初期実装を阻害しない範囲で、後続タスクとして分離して扱う
- `AGIC` / App Gateway は、AKS にアプリを載せるための「絶対条件」ではない
  - 先に Helm chart を作り、ClusterIP / internal Service 前提でアプリを載せることはできる
  - Ingress / 外部公開をどうするかは、その後に App Gateway / AGIC / 別 ingress controller の判断でよい
- Helm の前に「values 相当の設定整理」は必須
  - `values.yaml` というファイル名に限らず、少なくとも
    - デフォルト値
    - 環境差分
    - Secret ではない設定
    を整理しないと chart は作れない
- Step 7 では frontend も AKS に載せる対象に含める
  - ただし backend と同じ chart にはまとめず、
  - `k8s/charts/backend` と `k8s/charts/frontend` を別 chart として並行に整備する
  - 初期段階では `k8s/manifests` は作らず、Helm chart を正とする
  - 初期段階の障害切り分けをしやすくするため、まずは分離を優先する
  - 将来必要なら、後から統合する余地は残す
  - frontend も初期実装では `ClusterIP` 固定で進め、
    Ingress / App Gateway 連携は後続タスクとして追加する

### 3.2 未実装

- API / cleanup / worker の Helm chart
- frontend の Helm chart
- API 用 `Deployment` / `Service`
- cleanup 用 `CronJob`
- worker 用 `Deployment`
- `ScaledObject`
- Workload Identity 用 `ServiceAccount` / annotation / values
- Service Bus / Blob / DB などの本番 values 整備
- Ingress / App Gateway 連携方針の確定

## 4. Step 8. Staging / 運用検証

進捗: 一部完了

完了:

- ローカル実装は存在
- CI / lint / typecheck / test の一部は通過済み前提で進行

未完:

- Staging 上での CronJob 実行検証
- worker / queue / Blob の AKS 上検証
- App Insights / 実運用監視導線の確認
- DLQ 運用手順の確認

## 5. Step 9. リリース

進捗: 未着手

- 段階有効化
- Runbook 整備
- 本番切替手順の確定

## 6. Step 10. ドキュメント仕上げ（後続）

進捗: 未着手

- AKS / Helm / KEDA 実装後の運用手順を最終確定する
- Runbook を独立ドキュメントとして整備する
- 必要に応じて `docs/infra/*.md` の正式仕様へ反映する
- 本番切替手順の確定

## 7. 今後の作業ステップ（現時点の推奨順）

### 7.1 先に進めるべきもの

1. Azure 側で「先に必要なもの」を確定する
2. Helm に載せる values 項目を先に棚卸しする
3. Helm chart の骨組みを作る
4. API を先に chart 化して AKS 上で起動できるようにする
5. cleanup を `CronJob` として chart 化する
6. worker を job_type ごとに `Deployment` 化する
7. `KEDA ScaledObject` を worker ごとに追加する
8. Workload Identity の `ServiceAccount` / annotation / values を追加する
9. frontend を別 chart として整備する
10. Ingress / App Gateway 連携方針を確定する
11. Staging で cleanup / worker / queue / Blob の疎通を検証する
12. CI から呼ぶコンテナ build / deploy 手順を確定する
13. Runbook と本番リリース手順を確定する

### 7.2 Helm 実装タスク

1. values の棚卸しを先に行う
   - まず `values.yaml` と `values.staging.yaml` / `values.prod.yaml` のどちらで分けるかを決める
   - 少なくとも以下を values 化する
     - backend / frontend の image repository / tag / pullPolicy
     - `SERVICE_NAME`
     - `API_LOG_LEVEL`
     - `FRONTEND_BASE_URL`
     - `CSRF_TRUSTED_ORIGINS`
     - `ASYNC_JOB_*`
     - `SERVICE_BUS_*`
     - `AZURE_BLOB_*`
     - `DATABASE_*`（Secret へ逃がすものを除く）
     - worker replica / KEDA scale 設定
     - cleanup schedule
     - frontend の最小 env（例: backend API の base URL）
2. `k8s/charts/backend` を新設する
3. backend 共通テンプレートを先に作る
   - `ServiceAccount`
   - `ConfigMap`
   - `Secret` 参照
   - 共通 label / name helper
4. API 用 `Deployment` / `Service` を追加する
   - まずは Ingress を持たず、`ClusterIP` 前提で起動確認できる状態にする
5. cleanup 用 `CronJob` を追加する
   - `sessions cleanup`
   - `audit retention cleanup`
   - `jobs cleanup`
     - 非同期ジョブが生成した期限切れ Blob 成果物の定期削除
     - stale `running` ジョブの `failed` 化
6. worker 用 `Deployment` を追加する
   - `auth-audit-export`
   - `sample-wait-blob`
   - それぞれ `WORKER_MODULE` を変える
7. `KEDA ScaledObject` を追加する
   - queue ごとに 1 つずつ持つ
   - `messageCount` / `minReplicaCount` / `maxReplicaCount` を values 化する
8. Workload Identity を追加する
   - API 用 `ServiceAccount`
   - worker 用 `ServiceAccount`
   - 必要なら cleanup 用 `ServiceAccount`
   - annotation / client ID 参照を values 化する
9. `k8s/charts/frontend` を新設する
10. frontend の最小 chart を作る
   - `Deployment`
   - `Service`
   - `ClusterIP`
11. Ingress の扱いを決める
   - Step 7 の chart 初期実装では「Ingress なし」でもよい
   - App Gateway / AGIC を使う場合は、その後に別テンプレートで追加する
12. Secret 取り込み方式を決める
   - `Secret` を Helm 管理するか
   - 既存 Secret を参照するだけにするか
   - Key Vault CSI / External Secrets を使うか
   - Key Vault の Secret を CSI volume として Pod にマウントする方式を採るかも、この段階で判断する

現時点で確定している values / Secret 方針:

- Secret の正本は Key Vault を前提とする
- Pod へは Kubernetes `Secret` 経由で env var として渡す
- Helm では平文の秘密値は持たない
- Secret は用途ごとに分ける
  - 例: DB / auth / Azure 接続
- `DATABASE_URL` は 1 つの Secret 値として扱う
- 認証系では、秘密値だけを Secret として扱う
  - `SESSION_SECRET_KEY`
  - `ENTRA_CLIENT_SECRET`
  - `ENTRA_TOKEN_ENCRYPTION_KEY`
- `ENTRA_TENANT_ID` / `ENTRA_CLIENT_ID` は ConfigMap / values 側で扱う
- Service Bus / Blob は本番でキーレス前提とする
  - `SERVICE_BUS_CONNECTION_STRING` は本番 Helm では扱わない
  - `AZURE_BLOB_CONNECTION_STRING` は本番 Helm では扱わない
  - `SERVICE_BUS_USE_CONNECTION_STRING` は本番 Helm では持たず、常に `false` 前提
  - `AZURE_BLOB_USE_CONNECTION_STRING` は本番 Helm では持たず、常に `false` 前提
- `SERVICE_BUS_NAMESPACE_FQDN`
- queue 名
- `AZURE_BLOB_ACCOUNT_URL`
- `AZURE_BLOB_CONTAINER`
  は ConfigMap / values 側で扱う
- `FRONTEND_BASE_URL` と `CSRF_TRUSTED_ORIGINS` は values で明示的に持つ
- API の `Service` は最終構成に合わせて `ClusterIP` 固定で持つ
- worker のスケール設定は job_type ごとに個別に持つ
  - `minReplicaCount`
  - `maxReplicaCount`
  - `queueLengthThreshold`
- cleanup の schedule は `sessions` / `audit` / `jobs` ごとに個別に持つ
  - `schedule`
  - `suspend`
  - `concurrencyPolicy`
- cleanup の `CronJob` は
  - `sessions`
  - `audit`
  - `jobs`
  の 3 本に分けて持つ
- `ServiceAccount` / `Managed Identity` は
  - API 用
  - worker 用
  - cleanup 用
  で分ける
- worker は job_type ごとには分けず、worker 用 `ServiceAccount` / `Managed Identity` を 1 つにまとめる
- Helm values は
  - `values.yaml`
  - `values.staging.yaml`
  - `values.prod.yaml`
  の `base + 環境別オーバーライド` 構成で持つ
- backend は `k8s/charts/backend`、frontend は `k8s/charts/frontend` の別 chart で管理する
- 初期段階では `k8s/manifests` は作らず、Helm chart の template を manifest の正本として扱う
- frontend の image 設定は
  - `frontend.image.repository`
  - `frontend.image.tag`
  - `frontend.image.pullPolicy`
  の基本 3 点で持つ
- frontend の env は広く一般化せず、backend API の base URL など必要最小限だけを values で持つ
- frontend が参照する backend API の接続先は、`https://.../backend` のような完全な base URL を
  1 つの values として持つ

backend chart で ConfigMap / values に載せる非 Secret 環境変数（現時点の具体名）:

- 基本設定
  - `SERVICE_NAME`
  - `API_LOG_LEVEL`
  - `API_PORT`
- DB 周辺（Secret を除く）
  - `DATABASE_ECHO`
  - `DATABASE_POOL_SIZE`
  - `DATABASE_MAX_OVERFLOW`
  - `DATABASE_POOL_TIMEOUT`
- 認証・セッション周辺（Secret を除く）
  - `EMAIL_VERIFICATION_TTL_MINUTES`
  - `PASSWORD_RESET_TTL_MINUTES`
  - `EMAIL_LOGIN_MAX_FAILURES`
  - `EMAIL_LOGIN_LOCK_MINUTES`
  - `ARGON2_TIME_COST`
  - `ARGON2_MEMORY_COST`
  - `ARGON2_PARALLELISM`
  - `ARGON2_HASH_LEN`
  - `ARGON2_SALT_LEN`
  - `SESSION_TTL_HOURS`
  - `SESSION_EXPIRED_GRACE_DAYS`
  - `SESSION_CLEANUP_ENABLED`
  - `AUTH_AUDIT_RETENTION_MONTHS`
  - `AUDIT_CLEANUP_ENABLED`
  - `CLEANUP_BATCH_SIZE`
  - `SESSION_COOKIE_NAME`
  - `SESSION_COOKIE_SECURE`
  - `SESSION_COOKIE_SAMESITE`
  - `AUTH_DEBUG_RETURN_TOKENS`
- 非同期ジョブ
  - `ASYNC_JOBS_ENABLED`
  - `ASYNC_JOB_MAX_ROWS_PER_JOB`
  - `ASYNC_JOB_DEFAULT_RETENTION_DAYS`
  - `ASYNC_JOB_RETENTION_MAX_DAYS`
  - `ASYNC_JOB_GLOBAL_CONCURRENCY`
  - `ASYNC_JOB_PER_USER_CONCURRENCY`
  - `ASYNC_JOB_RUNNING_TIMEOUT_SECONDS`
  - `ASYNC_JOB_AUTH_AUDIT_EXPORT_TASK_NAME`
  - `ASYNC_JOB_SAMPLE_WAIT_BLOB_TASK_NAME`
- Service Bus（本番キーレス）
  - `SERVICE_BUS_NAMESPACE_FQDN`
  - `SERVICE_BUS_AUTH_AUDIT_EXPORT_QUEUE_NAME`
  - `SERVICE_BUS_SAMPLE_WAIT_BLOB_QUEUE_NAME`
- Blob Storage（本番キーレス）
  - `AZURE_BLOB_ACCOUNT_URL`
  - `AZURE_BLOB_CONTAINER`
- frontend / Entra 連携（Secret を除く）
  - `FRONTEND_BASE_URL`
  - `AUTH_POST_LOGIN_DEFAULT_PATH`
  - `ENTRA_TENANT_ID`
  - `ENTRA_CLIENT_ID`
  - `ENTRA_REDIRECT_URI`
  - `ENTRA_INTERNAL_DOMAINS`
  - `CSRF_TRUSTED_ORIGINS`

backend chart で Secret として参照する環境変数（現時点の具体名）:

- `DATABASE_URL`
- `SESSION_SECRET_KEY`
- `ENTRA_CLIENT_SECRET`
- `ENTRA_TOKEN_ENCRYPTION_KEY`

frontend chart で values に載せる最小構成（現時点の具体名）:

- image
  - `frontend.image.repository`
  - `frontend.image.tag`
  - `frontend.image.pullPolicy`
- runtime
  - `frontend.replicaCount`
  - `frontend.service.port`
  - `frontend.resources`
- env
  - `VITE_BACKEND_BASE_URL`
  - `VITE_PRODUCT_NAME`

frontend chart は、現時点では Kubernetes `Secret` を使わず、非 Secret 値だけで構成する

後続タスク（未確定のため Step 7 内で別途実施）:

- Key Vault 連携の具体方式を確定する
  - `SecretProviderClass`（CSI Driver）を使うか
  - `ExternalSecret` を使うか
  - 既存 Kubernetes `Secret` への同期を別レイヤーで行うか
- Key Vault の Secret を CSI volume として Pod にマウントする方式を採る場合は、
  `Step 7.2` の Secret 取り込み方式の決定と合わせて設計する
- 上記が固まるまでは、Helm には「Secret 名 / key 名を参照する箱」だけを持たせる
- 具体的な Key Vault 連携 manifest のテンプレート化は、Step 7 の後半タスクとして追加する

参考メモ（未確定）:

- 現時点では、cleanup の Cron スケジュールはコード / Helm values に未反映で、要件確定前の参考値としてのみ扱う。
- 参考値の例:
  - `sessions cleanup`: 1時間ごと
  - `audit retention cleanup`: 1日1回
- これらは Helm / CronJob 実装時に正式決定し、確定後に要件へ昇格させる。
- cleanup 用 CronJob の最低限の運用要件として、`concurrencyPolicy: Forbid` を優先候補とする。
- これも Helm / CronJob 実装時に正式決定し、確定後に要件へ昇格させる。

### 7.3 Azure 側の先行作業

1. Resource Group を作成する
   - Step 7 の初期導入では、まず検証用の 1 つの Resource Group で十分
2. ACR を作成する
   - AKS と同じリージョンに置く
   - 初期導入では `Basic` で開始してよい
   - `RBAC レジストリのアクセス許可` を選び、ABAC は使わない
   - この段階では `Customer-managed keys` は使わず、必要になった時点で `Premium` を検討する
3. AKS クラスタを作成する
   - まずはパブリック到達可能なシンプル構成でよい
   - まずは Azure Portal の `Dev/Test` プリセットを起点にする
   - Basic タブの推奨値
     - リージョン: `Japan East`
     - Availability Zones: `なし`
     - AKS 価格レベル: `無料`
     - 長期的なサポート: `オフ`
     - Kubernetes バージョン: 既定の安定版
     - 自動アップグレード: `パッチで有効化`
     - ノード セキュリティ チャネル: `ノード イメージ`
     - 認証と認可: `Kubernetes RBAC を使用したローカル アカウント`
       - 初期導入では、まず `kubectl` と Helm を最短で使えることを優先する
   - ノードプール タブの推奨値
     - ノードの自動プロビジョニング: `オフ`
     - 追加ノードプール: 作成しない
     - ノードサイズ: `D2ps_v6`（2 vCPU / 8 GiB を目安にした小さめ構成）
     - スケーリング方法: `手動`
     - ノード数: `1`
       - もし Portal 事情で自動スケールを使う場合も、`最小 1 / 最大 2` 程度までに抑える
     - 仮想ノード: `オフ`
     - OS ディスク暗号化: 既定の `プラットフォーム マネージド キー`
   - ネットワーク タブの推奨値
     - プライベート クラスター: `オフ`
     - 承認された IP 範囲: `オフ`
     - ネットワーク構成: `Azure CNI オーバーレイ`
     - 独自の Azure 仮想ネットワークを持ち込む: `オフ`
     - Cilium データプレーン: `オフ`
     - ネットワーク ポリシー エンジン: `なし`
     - ロード バランサー: `Standard`
   - 統合 タブの推奨値
     - コンテナー レジストリ: 作成済みの `ACR` を選択する
     - Istio: `オフ`
     - Azure Policy: `無効`
   - 監視中 タブの推奨値
     - コンテナー ログ: `オフ`
     - Prometheus メトリック: `オフ`
     - Grafana: `オフ`
     - 推奨アラート ルール: `オフ`
       - 初期導入では `kubectl logs` と Pod 起動確認を優先し、監視追加は後回しにする
   - セキュリティ タブの推奨値
     - `Managed Identity` を有効にする
     - `OIDC issuer` を有効にする
     - `Workload Identity` を有効にする
     - Image Cleaner: `オフ`
     - Key Vault のシークレット ストア CSI ドライバー: `オフ`
       - Key Vault 連携の具体方式は `Step 7.2` の Secret 取り込み方式で後から決める
   - 詳細 タブの推奨値
     - インフラストラクチャ リソース グループ: 既定値のまま
     - マネージド Kubernetes 名前空間: 追加しない
   - Ingress / App Gateway はこの時点では必須ではない
4. ACR を AKS から pull できる状態にする
   - まずは `attach-acr` 相当で AKS から pull できる状態を優先する
5. AKS の OIDC issuer URL を確認する
   - 後続の federated credential 作成に必要
6. Azure 側の依存リソースを作成する
   - 既存利用
     - PostgreSQL
     - Storage Account
     - Service Bus
   - 新規作成
     - Key Vault
   - Redis はこの構成では使わない
7. 依存リソースの中身を作成する
   - この時点で作成済み
   - Storage Account
     - Blob container: `async-jobs`
   - Service Bus
     - queue: `auth-audit-export`
     - queue: `sample-wait-blob`
8. Workload Identity 用の User Assigned Managed Identity を作成する
   - API 用
   - worker 用
   - cleanup 用
   - 技術的には AKS より前でもよいが、初期導入では AKS 作成後の方が整理しやすい
   - Portal では `Managed Identity` の `ユーザー割り当て` を選んで 3 つ作成する
   - 推奨の命名例
     - `mi-3pull-api`
     - `mi-3pull-worker`
     - `mi-3pull-cleanup`
   - 配置先
     - サブスクリプション: 今回の検証用サブスクリプション
     - リソース グループ: `3pull-app`
     - リージョン: `Japan East`
   - この段階では、まだ federated credential は作らない
     - まずは Managed Identity 本体だけ作成する
     - federated credential は `12` で、Kubernetes の `ServiceAccount` 名確定後に作成する
   - 作成後に必ず控える値
     - `クライアント ID (clientId)`
     - `プリンシパル ID (principalId / objectId)`
     - `リソース ID`
   - 後続の用途
     - API 用: Service Bus 送信、Blob 読み取り、Key Vault 読み取り
     - worker 用: Service Bus 受信、Blob 読み書き、Key Vault 読み取り
     - cleanup 用: Blob 削除、Key Vault 読み取り
   - CLI で作る場合の例
     - `az identity create --resource-group 3pull-app --name mi-3pull-api --location japaneast`
     - `az identity create --resource-group 3pull-app --name mi-3pull-worker --location japaneast`
     - `az identity create --resource-group 3pull-app --name mi-3pull-cleanup --location japaneast`
9. Azure リソース側の RBAC を付与する
   - Service Bus
     - API: `Azure Service Bus Data Sender`
     - worker: `Azure Service Bus Data Receiver`
     - cleanup: 原則不要
   - Storage
     - worker: `Storage Blob Data Contributor`
     - cleanup: `Storage Blob Data Contributor`
     - API: 現行実装では Blob download もあるため、初期導入では `Storage Blob Data Contributor` を基本にする
   - Key Vault
     - API: `Key Vault Secrets User`
     - worker: `Key Vault Secrets User`
     - cleanup: `Key Vault Secrets User`
10. Key Vault に Secret を投入する
   - Key Vault の secret 名は `_` を使えないため、`-` 区切りで作成する
   - アプリ側の env var 名は従来どおり大文字スネークケースのまま扱う
   - `az` コマンドで設定する場合は `az keyvault secret set --vault-name <KEY_VAULT_NAME> --name <SECRET_NAME> --value <SECRET_VALUE>` を使う
   - Key Vault secret: `database-url`
     - env var: `DATABASE_URL`
     - 例: `az keyvault secret set --vault-name <KEY_VAULT_NAME> --name database-url --value <DATABASE_URL>`
   - Key Vault secret: `session-secret-key`
     - env var: `SESSION_SECRET_KEY`
     - secret 値は `openssl rand -hex 32` で生成したランダム文字列を使う
     - 例: `az keyvault secret set --vault-name <KEY_VAULT_NAME> --name session-secret-key --value "$(openssl rand -hex 32)"`
   - Key Vault secret: `entra-client-secret`
     - env var: `ENTRA_CLIENT_SECRET`
     - 例: `az keyvault secret set --vault-name <KEY_VAULT_NAME> --name entra-client-secret --value <ENTRA_CLIENT_SECRET>`
   - Key Vault secret: `entra-token-encryption-key`
     - env var: `ENTRA_TOKEN_ENCRYPTION_KEY`
     - secret 値は `openssl rand -hex 32` で生成したランダム文字列を使う
     - 例: `az keyvault secret set --vault-name <KEY_VAULT_NAME> --name entra-token-encryption-key --value "$(openssl rand -hex 32)"`
11. Kubernetes 側で使う ServiceAccount 名を確定する
   - このステップの目的は、Workload Identity の federated credential で使う `subject` を固定すること
   - 先に名前を固定しないと、`12` の federated credential 作成時に Azure 側の紐付け先を決められない
   - 初期導入でも namespace は専用のものを 1 つに固定して進める
     - 推奨: `3pull`
     - `default` は検証では簡単だが、本番運用では境界が曖昧になるため採用しない
     - namespace を変更すると、federated credential 側の `subject` も更新が必要
   - ServiceAccount 名は役割単位で固定する
     - API 用: `sa-3pull-api`
     - worker 用: `sa-3pull-worker`
     - cleanup 用: `sa-3pull-cleanup`
   - この段階で決めて控える値
     - namespace: `3pull`
     - API 用 ServiceAccount 名: `sa-3pull-api`
     - worker 用 ServiceAccount 名: `sa-3pull-worker`
     - cleanup 用 ServiceAccount 名: `sa-3pull-cleanup`
   - federated credential 作成時に使う subject は以下で固定する
     - API: `system:serviceaccount:3pull:sa-3pull-api`
     - worker: `system:serviceaccount:3pull:sa-3pull-worker`
     - cleanup: `system:serviceaccount:3pull:sa-3pull-cleanup`
   - 本番運用では、`ServiceAccount` は Helm 管理を正とする
     - backend chart の `ServiceAccount` template と values に同じ名前をそのまま反映する
     - `kubectl create serviceaccount` での手動作成は、初期検証や federated credential の切り分け用に限定する
     - 手動作成した `ServiceAccount` を残したまま Helm でも同名作成すると競合するため、Helm 導入前に削除して切り替える
   - 初期導入では、worker は job_type ごとに分けず、1 つの ServiceAccount を共用する
   - このステップでの具体作業
     - namespace を `3pull` で確定する
     - 上記 3 つの ServiceAccount 名を確定する
     - 各 Managed Identity と 1 対 1 で対応付ける
       - `mi-3pull-api` ↔ `sa-3pull-api`
       - `mi-3pull-worker` ↔ `sa-3pull-worker`
       - `mi-3pull-cleanup` ↔ `sa-3pull-cleanup`
     - `12` の federated credential 作成に使う subject をメモしておく
     - Helm chart 作成時に同じ名前を使う前提で values 設計へ反映する
12. 各 User Assigned Managed Identity に federated credential を作成する
   - AKS の OIDC issuer URL と Kubernetes `ServiceAccount` を結びつける
   - これは AKS 作成後でないと進められない
   - 先に AKS の OIDC issuer URL を確認する
     - `az aks show --resource-group 3pull-app --name <AKS_CLUSTER_NAME> --query "oidcIssuerProfile.issuerUrl" -o tsv`
   - federated credential の作成例
     - API:
       `az identity federated-credential create --resource-group 3pull-app --identity-name mi-3pull-api --name fic-3pull-api --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:3pull:sa-3pull-api" --audience "api://AzureADTokenExchange"`
     - worker:
       `az identity federated-credential create --resource-group 3pull-app --identity-name mi-3pull-worker --name fic-3pull-worker --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:3pull:sa-3pull-worker" --audience "api://AzureADTokenExchange"`
     - cleanup:
       `az identity federated-credential create --resource-group 3pull-app --identity-name mi-3pull-cleanup --name fic-3pull-cleanup --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:3pull:sa-3pull-cleanup" --audience "api://AzureADTokenExchange"`
   - 作成後は各 Managed Identity ごとに一覧確認する
     - `az identity federated-credential list --resource-group 3pull-app --identity-name mi-3pull-api`
     - `az identity federated-credential list --resource-group 3pull-app --identity-name mi-3pull-worker`
     - `az identity federated-credential list --resource-group 3pull-app --identity-name mi-3pull-cleanup`
13. Helm デプロイ前提の最終確認を行う
   - 目的は、Helm chart を作り始める前に Azure / Kubernetes 側の前提が揃っていることを確認すること
   - Key Vault を Kubernetes `Secret` に同期して使う場合は、AKS の `azure-keyvault-secrets-provider` add-on を有効にする
     - 例: `az aks enable-addons --addons azure-keyvault-secrets-provider --resource-group 3pull-app --name 3pull-test-cluster`
     - 有効化後、`kubectl get crd secretproviderclasses.secrets-store.csi.x-k8s.io` で CRD が存在することを確認する
   - AKS から ACR pull できることを確認する
     - 例: `az aks check-acr --resource-group 3pull-app --name <AKS_CLUSTER_NAME> --acr <ACR_NAME>`
     - `attach-acr` 済みでも、ここで明示的に疎通確認しておく
   - API / worker / cleanup の各 Managed Identity に必要な RBAC が付いていることを確認する
     - `az role assignment list --assignee <API_MI_PRINCIPAL_ID> --all`
     - `az role assignment list --assignee <WORKER_MI_PRINCIPAL_ID> --all`
     - `az role assignment list --assignee <CLEANUP_MI_PRINCIPAL_ID> --all`
     - 少なくとも以下が含まれることを確認する
       - API: `Azure Service Bus Data Sender` / `Storage Blob Data Contributor` / `Key Vault Secrets User`
       - worker: `Azure Service Bus Data Receiver` / `Storage Blob Data Contributor` / `Key Vault Secrets User`
       - cleanup: `Storage Blob Data Contributor` / `Key Vault Secrets User`
   - Key Vault に必要な Secret が入っていることを確認する
     - 例: `az keyvault secret list --vault-name <KEY_VAULT_NAME> -o table`
     - 少なくとも以下の 4 つがあることを確認する
       - `database-url`
       - `session-secret-key`
       - `entra-client-secret`
       - `entra-token-encryption-key`
   - Helm values に載せる Workload Identity 用 client ID を控える
     - `az identity show --resource-group 3pull-app --name mi-3pull-api --query clientId -o tsv`
     - `az identity show --resource-group 3pull-app --name mi-3pull-worker --query clientId -o tsv`
     - `az identity show --resource-group 3pull-app --name mi-3pull-cleanup --query clientId -o tsv`
     - 取得した client ID は、後続の `ServiceAccount` annotation に使う
   - Kubernetes 側で namespace / ServiceAccount が揃っていることを確認する
     - `kubectl get namespace 3pull`
     - `kubectl get serviceaccount -n 3pull`
     - `sa-3pull-api` / `sa-3pull-worker` / `sa-3pull-cleanup` が存在することを確認する
14. ネットワーク / App Gateway は後続フェーズとして扱う
   - VNet
   - private endpoint
   - App Gateway / AGIC
   - UDR
   - 2 重化構成
   は、AKS 上でアプリが動いた後に段階的に追加する
15. ACR へ push するコンテナイメージを build する
   - 現在の AKS ノードは `arm64` のため、少なくとも `linux/arm64` で動くイメージを作る
   - 将来の環境差分も考えると、`linux/amd64,linux/arm64` のマルチアーキテクチャ build を優先する
   - 事前に `docker buildx ls` で `buildx` が使えることを確認する
   - 現在の ACR login server は `cr3pulltest.azurecr.io`
   - push 前に ACR へログインする
     - `az acr login --name cr3pulltest`
   - tag は一意な値を使う
     - ここでは実行例として `20260303-01` を使う
   - API イメージ例
     - `docker buildx build --platform linux/amd64,linux/arm64 -f docker/api.Dockerfile -t cr3pulltest.azurecr.io/3pull-api:20260303-01 --push .`
   - worker イメージ例
     - `docker buildx build --platform linux/amd64,linux/arm64 -f docker/worker.Dockerfile -t cr3pulltest.azurecr.io/3pull-worker:20260303-01 --push .`
   - cleanup イメージ例
     - `docker buildx build --platform linux/amd64,linux/arm64 -f docker/cleanup.Dockerfile -t cr3pulltest.azurecr.io/3pull-cleanup:20260303-01 --push .`
   - frontend イメージ例
     - `docker buildx build --platform linux/amd64,linux/arm64 --build-arg VITE_BACKEND_BASE_URL=http://localhost:8000 --build-arg VITE_PRODUCT_NAME=3pull-web -f docker/web.Dockerfile -t cr3pulltest.azurecr.io/3pull-web:20260303-01 --push .`
     - `VITE_BACKEND_BASE_URL` と `VITE_PRODUCT_NAME` は必須。未指定なら build を失敗させる
16. ACR にイメージが push されたことを確認する
   - `az acr repository list --name cr3pulltest -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-api -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-worker -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-cleanup -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-web -o table`
17. API Pod: Helm 準備からデプロイまで
   - values を更新する
     - `k8s/charts/backend/values.yaml`
       - `api.image.repository`
       - `api.image.tag`
       - `api.image.pullPolicy`
       - `serviceAccounts.api.create`
       - `serviceAccounts.api.name`
       - `serviceAccounts.api.clientId`
       - `secretRefs.name`
       - `keyVault.vaultName`
       - `keyVault.tenantId`
       - `keyVault.secretProviderClassName`
       - `keyVault.secretName`
       - `keyVault.objects.*.keyVaultName`
       - `config.env.FRONTEND_BASE_URL`
       - `config.env.CSRF_TRUSTED_ORIGINS`
       - `config.env.SESSION_COOKIE_SECURE`
       - `config.env.ENTRA_REDIRECT_URI`
     - `k8s/charts/backend/values.staging.yaml`
       - staging だけ変える値だけを書く
   - 独自ドメイン未取得の間は、`port-forward` 前提で以下を使ってよい
     - `FRONTEND_BASE_URL=http://localhost:3000`
     - `CSRF_TRUSTED_ORIGINS=http://localhost:3000`
     - `SESSION_COOKIE_SECURE=false`
     - `ENTRA_REDIRECT_URI=http://localhost:8000/backend/auth/entra/callback`
   - manifest を確認する
     - `helm template 3pull-backend ./k8s/charts/backend -n 3pull -f ./k8s/charts/backend/values.yaml -f ./k8s/charts/backend/values.staging.yaml`
     - `helm upgrade --install 3pull-backend ./k8s/charts/backend -n 3pull --create-namespace -f ./k8s/charts/backend/values.yaml -f ./k8s/charts/backend/values.staging.yaml --dry-run`
   - 既存の手動作成済み `ServiceAccount` がある場合は、先に削除して Helm 管理へ切り替える
     - `kubectl delete serviceaccount -n 3pull sa-3pull-api sa-3pull-worker sa-3pull-cleanup`
   - デプロイする
     - `helm upgrade --install 3pull-backend ./k8s/charts/backend -n 3pull --create-namespace -f ./k8s/charts/backend/values.yaml -f ./k8s/charts/backend/values.staging.yaml`
18. Frontend Pod: Helm 準備からデプロイまで
   - values を更新する
     - `k8s/charts/frontend/values.yaml`
       - `frontend.image.repository`
       - `frontend.image.tag`
       - `frontend.image.pullPolicy`
       - `frontend.replicaCount`
       - `frontend.service.port`
     - `k8s/charts/frontend/values.staging.yaml`
       - staging だけ変える値だけを書く
   - 注意:
     - frontend chart は `VITE_*` を runtime values として持たない
     - backend 接続先を変える場合は、frontend image build 時に `VITE_BACKEND_BASE_URL` を埋め込んで作り直す
     - 現在の frontend build では `VITE_BACKEND_BASE_URL` は `http://localhost:8000` のように `/backend` を含めない
   - manifest を確認する
     - `helm template 3pull-frontend ./k8s/charts/frontend -n 3pull -f ./k8s/charts/frontend/values.yaml -f ./k8s/charts/frontend/values.staging.yaml`
     - `helm upgrade --install 3pull-frontend ./k8s/charts/frontend -n 3pull --create-namespace -f ./k8s/charts/frontend/values.yaml -f ./k8s/charts/frontend/values.staging.yaml --dry-run`
   - デプロイする
     - `helm upgrade --install 3pull-frontend ./k8s/charts/frontend -n 3pull --create-namespace -f ./k8s/charts/frontend/values.yaml -f ./k8s/charts/frontend/values.staging.yaml`
19. Worker / Cleanup Pod: Helm 準備からデプロイまで
   - worker 用 `Deployment` は実装済み
   - cleanup 用 `CronJob` は実装済み
   - `KEDA ScaledObject` は未実装
   - API と同じ順番で進める
     - values を更新する
     - `helm template` で確認する
     - `helm upgrade --install` でデプロイする
   - worker で最終的に必要になる値
     - `workers.authAuditExport.image.repository` / `tag`
     - `workers.sampleWaitBlob.image.repository` / `tag`
     - `serviceAccounts.worker.create`
     - `serviceAccounts.worker.name`
     - `serviceAccounts.worker.clientId`
     - queue 名
     - `workers.*.workerModule`
   - cleanup で最終的に必要になる値
     - `cleanup.image.repository` / `tag`
     - `serviceAccounts.cleanup.create`
     - `serviceAccounts.cleanup.name`
     - `serviceAccounts.cleanup.clientId`
     - `cleanup.jobs.sessions.schedule`
     - `cleanup.jobs.audit.schedule`
     - `cleanup.jobs.jobs.schedule`
     - `cleanup.jobs.*.command`
20. デプロイ後の動作確認を行う
   - `kubectl get all -n 3pull`
   - `kubectl describe pod -n 3pull <POD_NAME>`
   - `kubectl logs -n 3pull <POD_NAME>`
   - API は最低限 `readyz` / `livez` / `/backend/health` の応答を確認する
   - 独自ドメイン未取得の段階では、`port-forward` でブラウザ検証する
     - backend:
       - `kubectl port-forward -n 3pull svc/<BACKEND_SERVICE_NAME> 8000:8000`
       - 確認先: `http://localhost:8000/readyz`
       - 確認先: `http://localhost:8000/livez`
       - 確認先: `http://localhost:8000/backend/health`
     - frontend:
       - `kubectl port-forward -n 3pull svc/<FRONTEND_SERVICE_NAME> 3000:3000`
       - 確認先: `http://localhost:3000`
     - frontend から backend を呼ぶ検証では、frontend image の build 時点で `VITE_BACKEND_BASE_URL=http://localhost:8000` を埋め込んだ image を使う
   - `ImagePullBackOff` が出た場合は ACR 名、tag、アーキテクチャ、AKS の ACR 参照権限を見直す
21. worker / cleanup / frontend を段階的に追加する
   - worker / cleanup / frontend の最小実装は完了済み
   - 現時点でこのステップで追加対象になるのは、主に KEDA / Ingress / App Gateway
   - KEDA を実装する手順
     - 1. KEDA 本体を AKS にインストールする
       - `helm repo add kedacore https://kedacore.github.io/charts`
       - `helm repo update`
       - `helm upgrade --install keda kedacore/keda -n keda --create-namespace`
     - 2. CRD が入ったことを確認する
       - `kubectl get crd scaledobjects.keda.sh`
       - `kubectl get crd triggerauthentications.keda.sh`
     - 3. backend chart の values に worker ごとの KEDA 設定を追加する
       - `minReplicaCount`
       - `maxReplicaCount`
       - `queueLengthThreshold`
       - `pollingInterval`
       - `cooldownPeriod`
     - 4. worker ごとに `ScaledObject` template を追加する
       - `scaleTargetRef.name` は `r-<system名>-worker-...`
       - trigger は Azure Service Bus queue を使う
     - 5. KEDA が Service Bus を読むための認証方式を追加する
       - `TriggerAuthentication` を追加する
       - worker 用 Managed Identity / Workload Identity を使う前提で構成する
     - 6. `helm template` で `ScaledObject` / `TriggerAuthentication` を確認する
     - 7. `helm upgrade --install 3pull-backend ...` を再実行して反映する
     - 8. queue が空のときに worker が `0` 台まで落ちることを確認する
       - 目標: `minReplicaCount: 0`
   - Ingress / App Gateway を実装する手順
     - 1. 外部公開方式を決める
       - AKS Ingress Controller を使うか
       - App Gateway / AGIC を使うか
     - 2. 公開用の実ドメインと DNS を用意する
     - 3. backend / frontend chart に Ingress template を追加する
     - 4. `FRONTEND_BASE_URL` / `CSRF_TRUSTED_ORIGINS` / `ENTRA_REDIRECT_URI` を実ドメインへ切り替える
     - 5. frontend image も本番 URL 向け `VITE_BACKEND_BASE_URL` を埋め込んで再 build する
     - 6. `helm upgrade --install` で反映し、ブラウザからの疎通を確認する
   - 追加後の確認観点
     - worker: queue 投入時だけ Pod が起動 / 増減する
     - cleanup: CronJob が定刻実行される
     - frontend: 外部 URL からログイン画面表示、API 呼び出し、Entra callback が成立する

### 7.4 Staging / 本番検証タスク

1. Service Bus の送受信権限を確認する
2. Blob Storage の Data Plane RBAC を確認する
3. worker から queue 受信できることを確認する
4. worker から Blob upload / download / delete できることを確認する
5. cleanup CronJob の dry-run / 本実行ログを確認する
6. `jobs cleanup` により、期限切れの非同期ジョブ Blob 成果物が削除されることを確認する
7. DLQ 運用手順を確認する
8. stuck job が cleanup で `failed` 化されることを確認する

## 8. 現時点の判断メモ

### 8.1 すでに確定しているもの

- backend / frontend は別 chart で管理する
- API / frontend の `Service` は最終構成に合わせて `ClusterIP` 固定で進める
- Ingress / App Gateway は後続フェーズで追加する
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

Kubernetes 配備作業が完了といえる条件は、次のとおりです。

1. cleanup（sessions / audit / jobs）がコンテナ・Helm・AKS まで一貫して動く
2. async jobs（API / queue / worker / Blob）が AKS 上で動く
3. frontend が AKS 上で配信できる
4. Workload Identity で Service Bus / Blob に接続できる
5. `KEDA` により worker が queue 長に応じてスケールする
6. Docker / Helm / values / Runbook が揃う
7. README / docs が現行実装と一致している
