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
| Storage Account コンテナ作成 | Bicep 推奨 | 実装済み | `blobServices/containers` で作成可能 |
| Service Bus キュー作成 | Bicep 推奨 | 実装済み | `queues` で作成可能 |
| federated credential 作成 | Bicep 推奨 | 未実装 | `federatedIdentityCredentials` で作成可能 |
| Key Vault への Secret 値投入 | Script + CI Secret 管理 | 未実装 | 値は IaC に入れない |
| KEDA デプロイ | Helm（Makefile + CI） | 一部実装 | chart は実装済み。CI/Makefile 導線は未整備 |
| KEDA annotation（keda-operator） | Helm values 管理推奨 | 一部実装 | backend ServiceAccount 側は実装済み。keda-operator 側の運用固定化は残あり |

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

## 5. 今回の具体回答（質問への直接回答）

- `aks構築` -> Bicep でやる
- `マネージドid` -> Bicep で AKS と同じデプロイ単位で作る
- `Key VaultのRBAC` -> Bicep でできる（推奨）
- `Service BusのRBAC` -> Bicep でできる（推奨）
- `StorageのRBAC` -> Bicep でできる（推奨）
- `Storage Accountのコンテナ作成` -> Bicep でできる。初期構築のみなら Script でも可だが、冪等運用は Bicep 推奨
- `Service Busのキュー作成` -> Bicep でできる。初期構築のみでも Bicep 管理推奨
- `federated credential 作成` -> Bicep でできる（推奨）
- `Key Vault に Secret を投入` -> Script + Makefile + CI Secret 管理で実施（Bicepに生値は載せない）
- `KEDAデプロイ` -> Helm（Makefile/CI）で実施
- `KEDAのannotation` -> Helm values で管理（暫定は手動可だが恒久は Helm）

## 6. 次アクション（未完了タスク）

1. `infra/bicep` に federated credential 作成を追加
2. `scripts/` に Key Vault secret 投入スクリプトを追加
3. `Makefile` に `infra`, `bootstrap-secrets`, `deploy-keda`, `deploy-app` を分離追加
4. CI を `infra -> bootstrap -> app` の 3 ジョブ構成に分割
5. keda-operator 側の Workload Identity 設定を Helm values 管理へ固定化
