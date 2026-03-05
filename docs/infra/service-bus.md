# Service Bus

## Service Bus Namespace 本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | sb-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| SKU | Premium | sku.name |
| キャパシティ | 1 | sku.capacity |
| パブリックアクセス | Disabled | properties.publicNetworkAccess |
| TLS 最小バージョン | 1.2 | properties.minimumTlsVersion |
| ローカル認証無効化 | true | properties.disableLocalAuth |
| ゾーン冗長化 | false（初期値） | properties.zoneRedundant |

## 診断設定

- 対象: Service Bus Namespace（`Microsoft.ServiceBus/namespaces`）
- ログ: `allLogs`, `audit`
- メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- Service Bus Namespace 本体に削除ロックを適用
- Private Endpoint に削除ロックを適用
- Private DNS ゾーンに削除ロックを適用（`network.enableCentralizedPrivateDns=false` の場合のみ）

## リソース命名規則

- CAF の省略形ルールに準拠し、Service Bus Namespace は `sb` を利用します。
- そのため命名は `sb-[common.environmentName]-[common.systemName]` を基本とします。
- Namespace 名は英小文字・数字・ハイフンを使用し、先頭英字、末尾英数字とします。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## アクセス権（RBAC）方針

- 認証は Managed Identity + Azure RBAC を前提とします（接続文字列配布はしない）。
- 代表ロール:
  - API 用 MI: `Azure Service Bus Data Sender`
  - worker 用 MI: `Azure Service Bus Data Receiver`
  - KEDA 用 MI: `Azure Service Bus Data Receiver`（queue 長メトリクス取得）
- RBAC 付与対象スコープ:
  - 原則 Namespace スコープ
  - 必要時のみ queue スコープへ絞り込み

## キュー作成方針

- IaC（Bicep）で作成し、初期状態を固定化します。
- 初期対象キュー:
  - `auth-audit-export`
  - `sample-wait-blob`
- 詳細設定（TTL / MaxDeliveryCount / LockDuration / DLQ 運用）は実装時に確定します。

## Private Endpoint

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | pep-sb-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| プライベートリンク接続名 | pep-sb-[common.environmentName]-[common.systemName] | properties.privateLinkServiceConnections.name |
| プライベートリンク対象ID | id(sb-[common.environmentName]-[common.systemName]) | properties.privateLinkServiceConnections.properties.privateLinkServiceId |
| グループID | namespace | properties.privateLinkServiceConnections.properties.groupIds |
| サブネットID | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet | properties.subnet.id |

## NSG（PrivateEndpointSubnet）方針

- Service Bus Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で `privatelink.servicebus.windows.net` を作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | privatelink.servicebus.windows.net | name |
| 場所 | global | location |

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 親 | pep-sb-[common.environmentName]-[common.systemName] | parent |
| 名前 | dnszg-sb-[common.environmentName]-[common.systemName] | name |
| プライベートDNSゾーン構成名 | privatelink-servicebus-windows-net | properties.privateDnsZoneConfigs.name |
| プライベートDNSゾーンID | id(privatelink.servicebus.windows.net) | properties.privateDnsZoneConfigs.properties.privateDnsZoneId |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 親 | privatelink.servicebus.windows.net | parent |
| 名前 | link-sb-to-vnet-[common.environmentName]-[common.systemName] | name |
| 場所 | global | location |
| 自動登録 | false | properties.registrationEnabled |
| 仮想ネットワークID | id(vnet-[common.environmentName]-[common.systemName]) | properties.virtualNetwork.id |

## 実装フェーズ

- Bicep 実装済み:
  - `infra/bicep/main.service-bus.bicep`
  - `infra/config/service-bus.json`
  - `infra/scripts/generate-service-bus-params.py`
  - `infra/main.sh` の param 生成と deploy フロー
  - `infra/common.parameter.json` の `resourceToggles.serviceBus`
