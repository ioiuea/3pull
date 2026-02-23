# Application Insights

## Application Insights 本体

| 項目                           | 設定値                                            | Bicepプロパティ名                          |
| ------------------------------ | ------------------------------------------------- | ------------------------------------------ |
| 名前                           | appi-[common.environmentName]-[common.systemName] | name                                       |
| 場所                           | [common.location]                                 | location                                   |
| Kind                           | web                                               | kind                                       |
| Application Type               | web                                               | properties.Application_Type                |
| Ingestion Mode                 | LogAnalytics                                      | properties.IngestionMode                   |
| データ保持日数                 | 365                                               | properties.RetentionInDays                 |
| Ingestion 用パブリックアクセス | Disabled                                          | properties.publicNetworkAccessForIngestion |
| Query 用パブリックアクセス     | Enabled                                           | properties.publicNetworkAccessForQuery     |
| 接続先 Log Analytics           | log-[common.environmentName]-[common.systemName]  | properties.WorkspaceResourceId             |

## 診断設定

- 対象: Application Insights（`Microsoft.Insights/components`）
- ログ: `allLogs`
- メトリック: `AllMetrics`（`timeGrain: PT1M`）
- 送信先: Log Analytics（`log-[common.environmentName]-[common.systemName]`）

## 削除ロック

- Application Insights 本体に削除ロックを適用します。
- `common.enableResourceLock=true` の場合のみロックを作成します。

## リソース命名規則

- CAF の省略形ルールを参考に、Application Insights は `appi` を利用します。
- そのため命名は `appi-[common.environmentName]-[common.systemName]` を基本とします。
- `environmentName` / `systemName` は Monitor 系リソース間で同一規約を使います。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## 依存関係

- Application Insights は Workspace 接続（`WorkspaceResourceId`）を前提とするため、
  同一環境の Log Analytics Workspace が先に存在する必要があります。
- `main.sh` では Log Analytics を先にデプロイし、その後に Application Insights をデプロイします。

## IaC 実装時の入力方法

- `resourceToggles.applicationInsights=true` の場合のみデプロイします。
- 設定値（保持日数 / IngestionMode など）は本設計書の固定値を使用します。
- 生成パラメータは `infra/params/application-insights.bicepparam` に出力されます。
