# Log Analytics Workspace

## Log Analytics Workspace 本体

| 項目                           | 設定値                                           | Bicepプロパティ名                          |
| ------------------------------ | ------------------------------------------------ | ------------------------------------------ |
| 名前                           | log-[common.environmentName]-[common.systemName] | name                                       |
| 場所                           | [common.location]                                | location                                   |
| SKU                            | PerGB2018                                        | properties.sku.name                        |
| データ保持日数                 | 365                                              | properties.retentionInDays                 |
| 日次データ上限 (GB/日)         | [logAnalytics.dailyQuotaGb] (既定値: -1)          | properties.workspaceCapping.dailyQuotaGb   |
| Ingestion 用パブリックアクセス | Disabled                                         | properties.publicNetworkAccessForIngestion |
| Query 用パブリックアクセス     | Enabled                                          | properties.publicNetworkAccessForQuery     |

### 日次データ上限の仕様

- `infra/common.parameter.json` の `logAnalytics.dailyQuotaGb` で設定します。
- 既定値は `-1` とし、無制限で取り込み可能にします。
- 任意の上限値を設定した場合、Workspace の日次取り込み上限として適用します。
- 想定する有効値は `-1` または `0` 以上の整数です。

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
- 日次データ上限は `logAnalytics.dailyQuotaGb` を入力値として参照し、未指定時は `-1` を使用します。
- 生成パラメータは `infra/params/log-analytics.bicepparam` に出力されます。
