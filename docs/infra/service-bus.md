# Service Bus

## Namespace

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | `sb-[common.environmentName]-[common.systemName]` | `name` |
| 場所 | `[common.location]` | `location` |
| SKU | `infra/config/service-bus.json` の `skuName`（既定: Premium） | `sku.name` |
| キャパシティ | `infra/config/service-bus.json` の `skuCapacity` | `sku.capacity` |
| Public Network Access | `Disabled` | `properties.publicNetworkAccess` |
| 最小TLS | `1.2` | `properties.minimumTlsVersion` |
| ローカル認証無効化 | `true` | `properties.disableLocalAuth` |

## キュー

初期キューは `infra/config/service-bus.json` の `queues` で管理します。

- `auth-audit-export`
- `sample-wait-blob`

## RBAC（Workload Identity）

対象リソースのデプロイが有効で、必要な Managed Identity が Azure 上に存在する場合に Bicep で付与。

| principal | ロール | スコープ | 用途 |
| --- | --- | --- | --- |
| `mi-[env]-[system]-api` | `Azure Service Bus Data Sender` | Namespace | API送信 |
| `mi-[env]-[system]-worker` | `Azure Service Bus Data Receiver` | Namespace | worker受信 |
| `mi-[env]-[system]-keda-operator` | `Azure Service Bus Data Receiver` | Namespace | KEDA監視（スケーリング判定） |

## Private Endpoint / DNS

- Private Endpoint: `pep-sb-[env]-[system]`
- Private DNS Zone: `privatelink.servicebus.windows.net`
- `network.enableCentralizedPrivateDns=true` の場合は環境側 DNS 作成をスキップ

## 診断設定 / ロック

- 診断設定: `allLogs`, `audit`, `AllMetrics` -> Log Analytics
- `enableResourceLock=true` の場合に Namespace/PEP/DNS へ削除ロック

## 実装ファイル

- `infra/bicep/main.service-bus.bicep`
- `infra/scripts/generate-service-bus-params.py`
- `infra/config/service-bus.json`
