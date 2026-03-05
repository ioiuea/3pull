# 実装作業の振り分け方針（Bicep / Script / Makefile-CI）

## 1. 目的

- `docs/kubernetes-task.md` で進めてきた内容をもとに、今後の実装作業をどの実行方式で管理するかを整理する。
- 判断軸は次の 3 つとする。
  - 冪等性: 何度実行しても同じ状態に収束させられるか
  - 秘密情報: 機密値を IaC に載せずに安全に扱えるか
  - 運用性: 初期構築だけか、継続運用でも実行されるか

## 2. 振り分け結論（一覧）

ステータス凡例:
- 実装済み: リポジトリに実装反映済み
- 一部実装: マニフェスト等はあるが運用導線（CI/Makefile など）が未整備
- 未実装: 方針のみで実装未着手

| 作業項目 | 推奨実行方式 | 実装ステータス | 補足 |
| --- | --- | --- | --- |
| AKS 構築 | Bicep | 実装済み | `infra` で管理 |
| Managed Identity 作成（api/worker/cleanup） | Bicep | 実装済み | AKS 構築タイミングで同時作成 |
| OIDC / Workload Identity / Key Vault CSI 有効化 | Bicep | 実装済み | AKS プロパティで固定化 |
| Key Vault / Service Bus / Storage の RBAC 付与 | Bicep | 実装済み | `roleAssignments` で冪等化可能 |
| Storage Account コンテナ作成 | Bicep | 実装済み | `blobServices/containers` で作成可能 |
| Service Bus キュー作成 | Bicep | 実装済み | `queues` で作成可能 |
| federated credential 作成 | Bicep | 実装済み | `main.federated-credential.bicep` で作成 |
| Helm values 生成（backend/frontend） | Script | 実装済み | `main.sh` 末尾で `values.generate.yaml` を自動生成 |
| Key Vault への Secret 値投入 | Script + CI Secret | 未実装 | bootstrap script で `az keyvault secret set`。GitHub Actions の `Secrets`（例: `DATABASE_URL`, `SESSION_SECRET_KEY`, `ENTRA_CLIENT_SECRET`, `ENTRA_TOKEN_ENCRYPTION_KEY`）から値を渡す。固定値は `Variables` を使用。値は IaC に入れない |
| KEDA デプロイ | Helm + Makefile + GitHub Actions | 一部実装 | chart は実装済み。deploy 導線（Makefile/CI）は未整備 |
| KEDA annotation（keda-operator） | Helm values 管理 | 一部実装 | 手動 annotation は廃止し、values/CI 注入に統一する |

## 3. 項目別の判断

### 3.1 Bicep でやるもの

以下は「環境のあるべき状態」を定義でき、かつ秘密情報の生値を持たないため Bicep 管理が適切。

- AKS 構築
- Managed Identity 作成
- OIDC issuer / Workload Identity / Key Vault CSI add-on 有効化
- RBAC 付与（Key Vault / Service Bus / Storage）
- Storage コンテナ作成
- Service Bus キュー作成
- federated credential 作成

### 3.2 Script / Makefile でやるもの

以下は「秘密値注入」や「実行環境依存」が強いため、Bicep へ直接埋め込まない。

- Key Vault Secret 値投入
  - 例: `DATABASE_URL`, `SESSION_SECRET_KEY`, `ENTRA_CLIENT_SECRET`, `ENTRA_TOKEN_ENCRYPTION_KEY`
  - `az keyvault secret set` を Script 化し、実値は CI の Secret Store から注入する

### 3.3 Helm / CI でやるもの

以下は Kubernetes アプリ配備レイヤのため、Bicep ではなく Helm 管理が適切。

- backend/frontend chart デプロイ
- KEDA chart デプロイ
- KEDA operator の Workload Identity 関連設定
  - chart values で `ServiceAccount` annotation と Pod label を管理する
  - `kubectl annotate` / `kubectl patch` は緊急復旧時のみ

## 4. 実行責務の分離（推奨）

1. `infra` パイプライン（Bicep）
   - Azure リソース作成
   - MI 作成
   - RBAC
   - federated credential
   - Service Bus キュー / Storage コンテナ

2. `platform-bootstrap` パイプライン（Script）
   - Key Vault Secret 値投入
   - 必要に応じて初期データ投入

3. `app-deploy` パイプライン（Helm）
   - KEDA デプロイ
   - backend/frontend デプロイ
   - values 切替（stg/prod）

## 次アクション（未完了タスク）

1. `scripts/` に Key Vault secret 投入スクリプトを追加
2. `Makefile` に `infra`, `bootstrap-secrets`, `deploy-keda`, `deploy-app` を分離追加
3. CI を `infra -> bootstrap -> app` の 3 ジョブ構成に分割
4. keda-operator 側の Workload Identity 設定を Helm values 管理へ固定化
