# Log Analytics Workspace

## Log Analytics Workspace 本体

| 項目                           | 設定値                                           | Bicepプロパティ名                          |
| ------------------------------ | ------------------------------------------------ | ------------------------------------------ |
| 名前                           | log-[common.environmentName]-[common.systemName] | name                                       |
| 場所                           | [common.location]                                | location                                   |
| SKU                            | PerGB2018                                        | properties.sku.name                        |
| データ保持日数                 | 365                                              | properties.retentionInDays                 |
| Ingestion 用パブリックアクセス | Disabled                                         | properties.publicNetworkAccessForIngestion |
| Query 用パブリックアクセス     | Enabled                                          | properties.publicNetworkAccessForQuery     |

## 診断設定

- 他リソース（Application Insights / Firewall / NSG など）の診断ログ送信先として利用します。

## 削除ロック

- Log Analytics Workspace 本体に削除ロックを適用します。
- `common.enableResourceLock=true` の場合のみロックを作成します。

## リソース命名規則

- CAF の省略形ルールを参考に、Log Analytics Workspace は `log` を利用します。
- そのため命名は `log-[common.environmentName]-[common.systemName]` を基本とします。
- 運用上の識別を優先し、短く一意な `environmentName` / `systemName` を使用します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## IaC 実装時の入力方法

- `resourceToggles.logAnalytics=true` の場合のみデプロイします。
- Workspace の SKU / 保持日数 / パブリックアクセス設定は本設計書の固定値を使用します。
- 生成パラメータは `infra/params/log-analytics.bicepparam` に出力されます。
