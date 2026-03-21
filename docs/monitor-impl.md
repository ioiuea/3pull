# Monitor Impl

## 1. このドキュメントの位置づけ

- 本ドキュメントは、backend アプリケーションの監視実装を `Application Insights` 前提で整理する。
- rate limit に限定しない backend 全体の監視基盤として扱う。
- `docs/apps/auth-rate-limit.md` から切り出した内容を含み、今後の監視実装の正本とする。

## 2. 背景

- Azure 上には既に `Application Insights` リソースが存在する。
- しかし、backend アプリ側では telemetry 送信の実装が未導入である。
- 現時点では structlog ベースのアプリログは出力しているが、`Application Insights` / `Azure Monitor` / `Log Analytics` に統合して活用する設計が未整備である。

## 3. 目的

- backend から `Application Insights` へ request / exception / dependency / logging telemetry を送信できるようにする。
- Azure Monitor / Log Analytics で backend の障害調査、性能分析、アラート設定ができるようにする。
- rate limit を含む backend 横断の監視基盤として再利用できる形にする。

## 4. 対象範囲

### 4.1 対象

- FastAPI backend 本体
- HTTP request / response
- 例外
- 外部依存呼び出し
  - Azure SQL
  - Azure Service Bus
  - Azure Blob Storage
  - Azure Managed Redis
- Python logging
- rate limit 関連ログ

### 4.2 非対象

- Azure インフラリソース側の診断設定そのもの
  - それぞれのリソースの `Diagnostic Settings` は別途 infra 管理とする
- WAF / Application Gateway / AKS platform metrics
- frontend 側のブラウザ telemetry

## 5. 採用方針

- backend アプリの telemetry 実装は `Azure Monitor OpenTelemetry Distro` を第一候補とする。
- 接続先は既存の `Application Insights` とし、`APPLICATIONINSIGHTS_CONNECTION_STRING` で関連付ける。
- `Application Insights` は workspace-based 前提とし、最終的な分析・横断検索は `Log Analytics` で行う。
- アラートは `Azure Monitor Alert` を利用する。

## 6. 収集対象

### 6.1 基本 telemetry

- HTTP request
- 例外
- dependency
- logging

### 6.2 rate limit 関連

- `auth.rate_limit.blocked`
- `auth.rate_limit.observed_only`
- `auth.rate_limit.request_check_failed`
- `auth.rate_limit.failure_record_failed`

### 6.3 将来検討

- custom event
  - policy 別 block
  - redis_error
- custom metric
  - policy 別 block 件数
  - redis_error 件数

## 7. 設定項目

- `APPLICATIONINSIGHTS_CONNECTION_STRING`

追加対象:
- `apps/backend/.env`
- `apps/backend/.env.example`
- `AppSettings`

## 8. 実装ステップ

1. telemetry 実装方針を `Application Insights + Azure Monitor OpenTelemetry` に固定する
2. 必要パッケージを整理する
   - 第一候補: `azure-monitor-opentelemetry`
   - 必要に応じて `opentelemetry-instrumentation-fastapi` など関連 package を検討する
3. backend 設定に `APPLICATIONINSIGHTS_CONNECTION_STRING` を追加する
4. startup / lifecycle で telemetry 初期化を実装する
   - `configure_azure_monitor(...)`
   - `service.name` など resource attribute を設定する
   - ローカル未設定時は telemetry 初期化をスキップする
5. FastAPI request / exception / dependency telemetry が Application Insights に送られることを確認する
6. Python logging を Application Insights に流す
7. rate limit 関連ログが Application Insights / Log Analytics 上で追跡できることを確認する
8. 必要に応じて custom event / custom metric を追加する
9. KQL を docs に追記する
10. Azure Monitor Alert 条件を docs に追記する

## 9. KQL / Alert 方針

今後整理する:
- block 件数の時系列
- redis_error 急増
- exception 急増
- request duration 悪化

## 10. 参考

- Azure Monitor OpenTelemetry overview
  - https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-overview
- Azure Monitor OpenTelemetry configuration
  - https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration
- Application Insights workspace-based resource
  - https://learn.microsoft.com/en-us/azure/azure-monitor/app/create-workspace-resource
