# Kubernetes タスク整理（現行）

## 1. 仕様整理

### 1.1 このドキュメントの目的

- AKS / Helm / KEDA / Workload Identity / リリース準備の進捗を、実装実態ベースで管理する。
- backend / frontend のアプリ実装詳細ではなく、Kubernetes 配備作業に限定して扱う。

### 1.2 現在の前提（2026-03-04 時点）

- `infra/` 配下の Bicep は最終的なプライベートネットワーク構成向け。
- 現在は検証フェーズとして、AKS を含む主要 Azure リソースは手動で作成済み。
- まずはパブリック通信ベースで、アプリ間通信と Helm の成立性確認を優先する。
- Ingress / App Gateway / private endpoint / UDR は後続フェーズで段階導入する。

### 1.3 対象範囲

- AKS への配備
- Helm chart（backend / frontend）
- KEDA（worker オートスケール）
- Workload Identity
- Staging 運用検証
- リリース準備（Runbook 含む）

対象外:

- backend / frontend の機能実装そのもの
- 最終ネットワーク設計の確定作業（`docs/infra-task.md` 管轄）

### 1.4 実装方針（確定）

- Helm chart を正本とし、`k8s/manifests` は作らない。
- backend と frontend は別 chart で管理する。
- 初期段階は backend / frontend とも Service を `ClusterIP` で運用する。
- worker は job_type ごとに Deployment を分ける。
- cleanup は `sessions / audit / jobs` の 3 CronJob に分ける。
- Secret の正本は Key Vault とし、Helm に平文 Secret は持たない。
- Service Bus / Blob は本番想定ではキーレス（Workload Identity + `DefaultAzureCredential`）を前提とする。

### 1.5 ステータス定義

- `完了`: 実装と最低限の動作確認が完了
- `進行中`: 実装はあるが、検証中または不具合対応中
- `未着手`: まだ実装していない
- `保留`: 後続フェーズで実施予定

## 2. 作業ステップサマリ

| Step | 作業 | ステータス | 現状サマリ |
|---|---|---|---|
| 1 | 検証前提の確定（手動作成 + パブリック通信） | 完了 | 方針を確定し、手動作成リソースで検証中 |
| 2 | backend Helm 基盤（helper/config/sa/secret連携） | 完了 | `k8s/charts/backend` で成立 |
| 3 | API 配備（Deployment/Service） | 完了 | Pod 起動・アクセス確認済み |
| 4 | cleanup 配備（CronJob 3本） | 完了 | CronJob テンプレート実装済み |
| 5 | worker 配備（job_type別 Deployment） | 完了 | worker Pod 起動確認済み |
| 6 | frontend 配備（Deployment/Service） | 完了 | web Pod 起動・アクセス確認済み |
| 7 | KEDA 実装（ScaledObject/TriggerAuthentication） | 進行中 | テンプレート実装済み、認証でエラー発生 |
| 8 | Workload Identity 検証（API/worker/schedulers） | 進行中 | API/worker/schedulers SA 注釈は実装済み、KEDA連携の詰めが必要 |
| 9 | Ingress / App Gateway 連携 | 保留 | フェーズ分離済み |
| 10 | Staging 運用検証（queue/blob/cron/DLQ） | 未着手 | KEDA解消後に本格着手 |
| 11 | Runbook / 本番切替手順 | 未着手 | 運用検証完了後に整備 |
| 12 | ドキュメント最終同期 | 進行中 | 本ドキュメントを再編中 |

## 3. 作業ステップ詳細

### 3.1 Step 1: 検証前提の確定（完了）

目的:

- private 化前に、最小構成で Kubernetes 配備の成立性を検証する。

完了内容:

- Azure リソースは手動作成で検証を進める方針を確定。
- パブリック通信前提で Helm / Pod 起動 / 疎通確認を先行。

残課題:

- なし（この方針は現フェーズで固定）。

### 3.2 Step 2: backend Helm 基盤（完了）

目的:

- backend の共通テンプレートと values 構造を確立する。

完了内容:

- chart 生成: `k8s/charts/backend`
- 実装済みテンプレート:
  - `_helpers.tpl`
  - `configmap.yaml`
  - `serviceaccounts.yaml`
  - `secretproviderclass.yaml`
- values の base + 環境差分構成を採用。

確認対象ファイル:

- `k8s/charts/backend/values.yaml`
- `k8s/charts/backend/templates/*`

### 3.3 Step 3: API 配備（完了）

目的:

- FastAPI を AKS 上で Deployment/Service として起動する。

完了内容:

- `api-deployment.yaml` / `api-service.yaml` 実装済み。
- `readyz` / `livez` / API アクセス確認は完了済み（報告ベース）。

残課題:

- Ingress 配備は後続フェーズ。

### 3.4 Step 4: cleanup 配備（完了）

目的:

- `sessions / audit / jobs` の定期 cleanup を CronJob 化する。

完了内容:

- `schedulers-cronjobs.yaml` 実装済み。
- schedule / suspend / concurrencyPolicy の values 化済み。

残課題:

- Staging での実行検証（dry-run / 本実行ログ確認）。

### 3.5 Step 5: worker 配備（完了）

目的:

- job_type ごとに worker Deployment を配備する。

完了内容:

- `worker-deployments.yaml` 実装済み。
- `auth-audit-export` / `sample-wait-blob` を個別 Deployment 化済み。
- worker Pod 起動確認は完了済み（報告ベース）。

残課題:

- KEDA スケール連携の正常化。

### 3.6 Step 6: frontend 配備（完了）

目的:

- frontend を AKS 上で最小構成で配備する。

完了内容:

- chart 生成: `k8s/charts/frontend`
- `deployment.yaml` / `service.yaml` 実装済み。
- web Pod 起動・アクセス確認は完了済み（報告ベース）。

残課題:

- Ingress / 外部公開は後続フェーズ。

### 3.7 Step 7: KEDA 実装（進行中）

目的:

- queue 長に応じて worker を自動スケールさせる。

完了内容:

- `keda-triggerauthentication.yaml` 実装済み。
- `keda-scaledobjects.yaml` 実装済み。
- worker ごとの KEDA values（min/max/polling/cooldown/threshold）追加済み。

発生中の問題（ブロッカー）:

- `docs/kedo.log` で以下エラーを確認。
  - `no client ID specified. Check pod configuration or set ClientID in the options`
  - `sources must contain at least one TokenCredential`
- 状態: KEDA が Azure Service Bus メトリクス取得時に認証情報を解決できていない。

次アクション:

1. KEDA の `TriggerAuthentication` 側に client ID を明示的に渡す方式へ修正。
2. Helm render で `TriggerAuthentication` / `ScaledObject` の最終 manifest を再確認。
3. 再デプロイ後、queue 空時 `minReplicaCount: 0` への収束を確認。

### 3.8 Step 8: Workload Identity 検証（進行中）

目的:

- API / worker / schedulers が Managed Identity で必要リソースへアクセスできることを担保する。

完了内容:

- ServiceAccount テンプレートで各 workload の clientId annotation を values 化済み。
- Pod 側の `azure.workload.identity/use: "true"` 付与済み。

未完了:

- KEDA 連携を含む end-to-end 認証確認。
- Staging での Service Bus / Blob / Key Vault の実運用相当検証。

### 3.9 Step 9: Ingress / App Gateway（保留）

目的:

- 外部公開導線を整備する。

現状:

- Step 分離済み。現フェーズでは未着手。
- 実施タイミングは KEDA と Workload Identity 検証完了後。

### 3.10 Step 10: Staging 運用検証（未着手）

実施項目:

- worker の queue 受信確認
- worker の Blob upload/download/delete 確認
- cleanup CronJob の定刻実行確認
- `jobs cleanup` の成果物削除確認
- DLQ 運用確認
- stuck job の `failed` 化確認

着手条件:

- Step 7（KEDA）ブロッカー解消。

### 3.11 Step 11: Runbook / 本番切替（未着手）

実施項目:

- 段階有効化手順
- 障害時ロールバック
- 定常運用手順
- 本番切替チェックリスト

着手条件:

- Staging 検証完了。

### 3.12 Step 12: ドキュメント同期（進行中）

目的:

- 実装との差分をなくし、判断しやすい状態を維持する。

今回反映した内容:

- 仕様整理・ステップサマリ・詳細の 3 層構成へ再編。
- 進捗ステータスを明示。
- 現在の主要ブロッカー（KEDA 認証）を明記。

## 4. 直近優先タスク

1. KEDA の clientId 連携修正（最優先）
2. KEDA 正常化後の worker スケール検証（0→N→0）
3. Staging 運用検証（queue / blob / schedulers / DLQ）
4. Ingress / App Gateway 方針確定と実装
5. Runbook / 本番切替手順の整備

## 5. 完了条件（Definition of Done）

1. cleanup（sessions / audit / jobs）が AKS 上で定期実行できる。
2. async jobs（API / queue / worker / Blob）が AKS 上で成立する。
3. frontend が AKS 上で配信できる。
4. Workload Identity で Service Bus / Blob / Key Vault に接続できる。
5. KEDA により worker が queue 長に応じてスケールする。
6. Docker / Helm / values / Runbook が揃う。
7. 本ドキュメントと実装状態が一致している。

## 6. 詳細作業手順（復元）

以下は、過去版 `docs/kubernetes-task.md` に記載していた詳細手順を抄訳せず復元したものです。

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
   - schedulers 用
   - 技術的には AKS より前でもよいが、初期導入では AKS 作成後の方が整理しやすい
   - Portal では `Managed Identity` の `ユーザー割り当て` を選んで 3 つ作成する
   - 推奨の命名例
     - `mi-3pull-api`
     - `mi-3pull-worker`
     - `mi-3pull-schedulers`
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
     - schedulers 用: Blob 削除、Key Vault 読み取り
   - CLI で作る場合の例
     - `az identity create --resource-group 3pull-app --name mi-3pull-api --location japaneast`
     - `az identity create --resource-group 3pull-app --name mi-3pull-worker --location japaneast`
     - `az identity create --resource-group 3pull-app --name mi-3pull-schedulers --location japaneast`
9. Azure リソース側の RBAC を付与する
   - Service Bus
     - API: `Azure Service Bus Data Sender`
     - worker: `Azure Service Bus Data Receiver`
     - schedulers: 原則不要
   - Storage
     - worker: `Storage Blob Data Contributor`
     - schedulers: `Storage Blob Data Contributor`
     - API: 現行実装では Blob download もあるため、初期導入では `Storage Blob Data Contributor` を基本にする
   - Key Vault
     - API: `Key Vault Secrets User`
     - worker: `Key Vault Secrets User`
     - schedulers: `Key Vault Secrets User`
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
11. Helm で作成する ServiceAccount 名を確定する
   - このステップの目的は、Helm values を正本として `ServiceAccount` 名を固定し、federated credential の `subject` を確定すること
   - `ServiceAccount` は手動作成せず、backend chart の `serviceAccounts.*` 設定から作成する
   - namespace も Helm デプロイ時の namespace を正とする
     - 推奨: `3pull`
     - namespace を変更すると、federated credential 側の `subject` も更新が必要
   - ServiceAccount 名は values で役割単位に固定する
     - API 用: `serviceAccounts.api.name`（例: `sa-3pull-api`）
     - worker 用: `serviceAccounts.worker.name`（例: `sa-3pull-worker`）
     - schedulers 用: `serviceAccounts.schedulers.name`（例: `sa-3pull-schedulers`）
     - KEDA operator 用: `keda` namespace の `keda-operator`（KEDA chart 側で作成）
   - この段階で確定・記録する値
     - Helm release namespace（例: `3pull`）
     - API 用 ServiceAccount 名
     - worker 用 ServiceAccount 名
     - schedulers 用 ServiceAccount 名
   - federated credential で使う subject は上記 values から組み立てる
     - API: `system:serviceaccount:<namespace>:<serviceAccounts.api.name>`
     - worker: `system:serviceaccount:<namespace>:<serviceAccounts.worker.name>`
     - schedulers: `system:serviceaccount:<namespace>:<serviceAccounts.schedulers.name>`
     - KEDA operator: `system:serviceaccount:keda:keda-operator`
   - このステップでの具体作業
     - `k8s/charts/backend/values.yaml` の `serviceAccounts.*.name` を最終確定する
     - `serviceAccounts.*.create: true` を維持する
     - `helm template` で `ServiceAccount` 名と namespace が想定どおりに render されることを確認する
     - render 結果を基に `subject` 文字列を確定して `12` へ渡す
12. 各 User Assigned Managed Identity に federated credential を作成する（Helm 管理の ServiceAccount を対象）
   - AKS の OIDC issuer URL と、Helm で作成される `ServiceAccount` の `subject` を結びつける
   - これは AKS 作成後でないと進められない
   - 先に AKS の OIDC issuer URL を確認する
     - `az aks show --resource-group 3pull-app --name <AKS_CLUSTER_NAME> --query "oidcIssuerProfile.issuerUrl" -o tsv`
   - `11` で確定した namespace / ServiceAccount 名を使って federated credential を作成する
   - federated credential の作成例
     - API:
       `az identity federated-credential create --resource-group 3pull-app --identity-name mi-3pull-api --name fic-3pull-api --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:<namespace>:<serviceAccounts.api.name>" --audience "api://AzureADTokenExchange"`
     - worker:
       `az identity federated-credential create --resource-group 3pull-app --identity-name mi-3pull-worker --name fic-3pull-worker --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:<namespace>:<serviceAccounts.worker.name>" --audience "api://AzureADTokenExchange"`
     - schedulers:
       `az identity federated-credential create --resource-group 3pull-app --identity-name mi-3pull-schedulers --name fic-3pull-schedulers --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:<namespace>:<serviceAccounts.schedulers.name>" --audience "api://AzureADTokenExchange"`
    - KEDA operator（専用 Managed Identity を利用する場合）:
      `az identity federated-credential create --resource-group 3pull-app --identity-name mi-<ENV>-3pull-keda-operator --name fic-<ENV>-3pull-keda-operator --issuer "<OIDC_ISSUER_URL>" --subject "system:serviceaccount:keda:keda-operator" --audience "api://AzureADTokenExchange"`
  - 現在の実装では、KEDA の `keda-operator` ServiceAccount annotation と Pod の Workload Identity 設定は `infra/main.sh` の KEDA Helm デプロイ時に自動設定する
    - `serviceAccount.operator.annotations.azure.workload.identity/client-id`
    - `podIdentity.azureWorkload.enabled=true`
    - `podIdentity.azureWorkload.clientId=<mi-<env>-<system>-keda-operator の clientId>`
   - 作成後は各 Managed Identity ごとに一覧確認する
     - `az identity federated-credential list --resource-group 3pull-app --identity-name mi-3pull-api`
     - `az identity federated-credential list --resource-group 3pull-app --identity-name mi-3pull-worker`
     - `az identity federated-credential list --resource-group 3pull-app --identity-name mi-3pull-schedulers`
     - KEDA operator 用を別 Managed Identity で運用する場合は、その identity でも同様に確認する
13. Helm デプロイ前提の最終確認を行う
   - 目的は、Helm chart を作り始める前に Azure / Kubernetes 側の前提が揃っていることを確認すること
   - Key Vault を Kubernetes `Secret` に同期して使う場合は、AKS の `azure-keyvault-secrets-provider` add-on を有効にする
     - 例: `az aks enable-addons --addons azure-keyvault-secrets-provider --resource-group 3pull-app --name 3pull-test-cluster`
     - 有効化後、`kubectl get crd secretproviderclasses.secrets-store.csi.x-k8s.io` で CRD が存在することを確認する
   - AKS から ACR pull できることを確認する
     - 例: `az aks check-acr --resource-group 3pull-app --name <AKS_CLUSTER_NAME> --acr <ACR_NAME>`
     - `attach-acr` 済みでも、ここで明示的に疎通確認しておく
   - API / worker / schedulers の各 Managed Identity に必要な RBAC が付いていることを確認する
     - `az role assignment list --assignee <API_MI_PRINCIPAL_ID> --all`
     - `az role assignment list --assignee <WORKER_MI_PRINCIPAL_ID> --all`
     - `az role assignment list --assignee <CLEANUP_MI_PRINCIPAL_ID> --all`
     - 少なくとも以下が含まれることを確認する
       - API: `Azure Service Bus Data Sender` / `Storage Blob Data Contributor` / `Key Vault Secrets User`
       - worker: `Azure Service Bus Data Receiver` / `Storage Blob Data Contributor` / `Key Vault Secrets User`
       - schedulers: `Storage Blob Data Contributor` / `Key Vault Secrets User`
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
     - `az identity show --resource-group 3pull-app --name mi-3pull-schedulers --query clientId -o tsv`
     - 取得した client ID は、後続の `ServiceAccount` annotation に使う
   - Kubernetes 側で namespace / ServiceAccount が揃っていることを確認する
     - `kubectl get namespace 3pull`
     - `kubectl get serviceaccount -n 3pull`
     - `sa-3pull-api` / `sa-3pull-worker` / `sa-3pull-schedulers` が存在することを確認する
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
   - schedulers イメージ例
     - `docker buildx build --platform linux/amd64,linux/arm64 -f docker/schedulers.Dockerfile -t cr3pulltest.azurecr.io/3pull-schedulers:20260303-01 --push .`
   - frontend イメージ例
     - `docker buildx build --platform linux/amd64,linux/arm64 --build-arg VITE_BACKEND_BASE_URL=http://localhost:8000 --build-arg VITE_PRODUCT_NAME=3pull-web -f docker/web.Dockerfile -t cr3pulltest.azurecr.io/3pull-web:20260303-01 --push .`
     - `VITE_BACKEND_BASE_URL` と `VITE_PRODUCT_NAME` は必須。未指定なら build を失敗させる
16. ACR にイメージが push されたことを確認する
   - `az acr repository list --name cr3pulltest -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-api -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-worker -o table`
   - `az acr repository show-tags --name cr3pulltest --repository 3pull-schedulers -o table`
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
     - `kubectl delete serviceaccount -n 3pull sa-3pull-api sa-3pull-worker sa-3pull-schedulers`
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
   - schedulers 用 `CronJob` は実装済み
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
     - `schedulers.image.repository` / `tag`
     - `serviceAccounts.schedulers.create`
     - `serviceAccounts.schedulers.name`
     - `serviceAccounts.schedulers.clientId`
     - `schedulers.jobs.sessions.schedule`
     - `schedulers.jobs.audit.schedule`
     - `schedulers.jobs.jobs.schedule`
     - `schedulers.jobs.*.command`
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
21. worker / schedulers / frontend を段階的に追加する
   - worker / schedulers / frontend の最小実装は完了済み
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
     - 1. AGIC は Helm 管理へ統一する（AKS 側 `ingressApplicationGateway` addon は利用しない）
     - 2. 通常系/低遅延系はドメイン分離で公開する
       - 例: `api.3pull.com`（通常系）, `ll-api.3pull.com`（低遅延系, `ll` は `low-latency` の略）
     - 3. backend / frontend chart それぞれに Ingress template を追加する
       - frontend は通常系のみ公開する
       - backend は通常系 + 低遅延系（限定 API のみ）を公開する
     - 4. 低遅延対象 API は Ingress values の host/path 単位で明示管理する
     - 5. TLS は App Gateway 側で終端し、証明書も App Gateway 側で管理する
     - 6. `FRONTEND_BASE_URL` / `CSRF_TRUSTED_ORIGINS` / `ENTRA_REDIRECT_URI` を実ドメインへ切り替える
     - 7. frontend image も本番 URL 向け `VITE_BACKEND_BASE_URL` を埋め込んで再 build する
     - 8. app-deploy（Helm）で `helm upgrade --install` を実行して反映する
     - 9. 通常系/低遅延系を分離して監視・アラートを設定する
   - 追加後の確認観点
     - worker: queue 投入時だけ Pod が起動 / 増減する
     - schedulers: CronJob が定刻実行される
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
