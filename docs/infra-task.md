# Infra タスク整理

## 1. このドキュメントの位置づけ

- 本ドキュメントは、インフラ側で今後検討・実装が必要な項目を、設計メモとして整理するためのものです。
- 現時点で未確定の内容は「検討事項」、実装が必要な内容は「作業タスク」として扱います。
- 要件が固まった項目は、今後 `docs/infra/*.md` の各リソース設計へ昇格させます。

## 2. 現時点の前提

- 実行環境は `AKS` を前提とする。
- backend / worker は `Managed Identity / Workload Identity` 前提で Azure リソースへ接続する。
- 非同期ジョブ基盤は `Azure Service Bus + 専用 worker` を前提とする。
- 成果物保存は `Azure Storage Account (Blob)` を前提とする。
- Redis は引き続き利用対象だが、認証方式は `Managed Identity` 有効化を前提に再整理する。

## 3. 検討事項

### 3.1 App Gateway の二重化オプション

- 検討内容:
  - 通常の `App Gateway` に加えて、`Firewall 経路の UDR を付けない App Gateway` を別系統で持つ二重化オプションを検討する。
- 主な観点:
  - 障害時の迂回経路として使うのか
  - 常時 active/active にするのか
  - FW 経由あり / なしで、どこまで経路差を許容するか
  - DNS / 切替手順 / 運用監視をどうするか
- 未確定事項:
  - 正式に採用するか
  - 採用時の命名・サブネット・ルーティング分離

### 3.2 `main.sh` の 2 段階デプロイ

- 検討内容:
  - `VNet` 作成までを `Phase 1`
  - それ以降のリソース展開を `Phase 2`
  - という形で、`main.sh` を 2 段階に分ける構成を検討する。
- 意図:
  - ネットワーク基盤の先行確定
  - 後続リソースの依存関係整理
  - デプロイ失敗時の切り分け容易化
- 主な観点:
  - `Phase 1` と `Phase 2` を別スクリプトにするか
  - 1 つの `main.sh` でフェーズ指定引数を持たせるか
  - パラメータファイルの責務分割をどうするか

## 4. 作業タスク

### 4.1 マネージド ID の作成方針整理

- 各 Azure リソース / 実行主体に対して、どの単位でマネージド ID を分けるかを整理する。
- 最低限、以下の主体は分離前提で検討する。
  - AKS 上の API
  - AKS 上の worker
  - 必要なら cleanup / バッチ系
- 方針:
  - 最小権限を維持するため、送信主体・受信主体・Blob 操作主体は可能な限り分ける。

### 4.2 Storage Account のマネージド ID 前提化

- Storage Account 側で、`Managed Identity` 前提のアクセスへ移行できるよう構成を整理する。
- アプリケーション接続は Shared Key 常用を避け、`Managed Identity / Workload Identity` を標準にする。
- 必要な作業:
  1. Storage Account の認可方針を `Managed Identity` 利用前提に整理する
  2. API / worker からのアクセス主体を決める
  3. ローカル例外時のフォールバック運用を決める

### 4.3 Storage Account への RBAC 付与

- AKS 側のマネージド ID から Storage Account へアクセスできるように RBAC を付与する。
- 現時点の基本方針:
  - `Storage Blob Data Contributor` を基本候補とする
- 対象:
  - API
  - worker
- 今後の確認事項:
  - API と worker の ID を分けた場合、API は Reader に落とせるか
  - コンテナ作成をアプリが担うか、IaC / 初期化手順へ分離するか

### 4.4 Redis のマネージド ID 有効化

- Redis に対して `Managed Identity` を使う構成へ寄せられるかを検討・実装する。
- 主な観点:
  - 現在の Redis 利用用途
  - 認証方式の切替可否
  - アプリ側設定変更の影響
- 未確定事項:
  - Redis 自体を今後どこまで残すか
  - Managed Identity 化の対象範囲

### 4.5 Service Bus の追加

- 非同期ジョブ基盤用に `Azure Service Bus` を追加する。
- 前提:
  - 本番は `Workload Identity`
  - ローカルは `az login + DefaultAzureCredential`
- 必要な作業:
  1. Service Bus namespace を作成する
  2. 認証方式を Entra 前提で整理する
  3. 必要なら本番で `SAS / ローカル認証` を無効化する

### 4.6 Service Bus の RBAC 設計

- Service Bus に対して、API と worker で役割ごとの RBAC を付与する。
- 現時点の方針:
  - API: `Azure Service Bus のデータ送信者`
  - worker: `Azure Service Bus のデータ受信者`
- 対象:
  - API 用マネージド ID
  - worker 用マネージド ID
- 検討事項:
  - namespace 単位で付与するか
  - queue 単位でより細かく分けるか

### 4.7 Service Bus のキュー作成

- 非同期ジョブ用キューを作成する。
- 現時点の標準キュー名:
  - `auth-audit-export`
  - `sample-wait-blob`
- 今後の作業:
  1. queue 作成方法を IaC に寄せる
  2. `maxDeliveryCount` などの初期値を IaC / 設定に反映する
  3. 将来ジョブ追加時の queue 追加手順を標準化する

## 5. 推奨実装順

1. `main.sh` の 2 段階デプロイ方針を決める
2. 各実行主体のマネージド ID 分離方針を決める
3. Storage Account の RBAC を整理する
4. Redis の Managed Identity 方針を整理する
5. Service Bus namespace を追加する
6. Service Bus の RBAC を API / worker で分ける
7. Service Bus の queue を作成する
8. App Gateway 二重化オプションの採否を決める

## 6. 要件へ昇格する条件

- ここに書かれている項目は、設計・実装内容が確定した段階で `docs/infra/*.md` の正式仕様へ反映する。
- 未確定の構成案は、このファイルでは残してよいが、正式仕様側には反映しない。
- 特に以下は、決定後に個別インフラドキュメントへ昇格させる。
  - App Gateway 二重化オプション
  - `main.sh` の 2 段階デプロイ
  - 各マネージド ID の責務分離
  - Storage / Redis / Service Bus の認証・RBAC
  - Service Bus の queue 設定
