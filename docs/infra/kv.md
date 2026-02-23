# Key Vault

## Key Vault 本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | kv-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| SKU Family | A | properties.sku.family |
| SKU Name | standard | properties.sku.name |
| RBAC有効化 | true | properties.enableRbacAuthorization |
| パブリックアクセス | Disabled | properties.publicNetworkAccess |
| ソフトデリート | true | properties.enableSoftDelete |
| パージ保護 | true | properties.enablePurgeProtection |
| 論理削除保持日数 | 90 | properties.softDeleteRetentionInDays |

## 診断設定

- 対象: Key Vault 本体（`Microsoft.KeyVault/vaults`）
- ログ: `allLogs`, `audit`
- メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- Key Vault 本体に削除ロックを適用
- Private Endpoint に削除ロックを適用
- Private DNS ゾーンに削除ロックを適用（`network.enableCentralizedPrivateDns=false` の場合のみ）

## リソース命名規則

- CAF の省略形ルールに準拠し、Key Vault は `kv` を利用します。
- そのため命名は `kv-[common.environmentName]-[common.systemName]` を基本とします。
- 文字数制約（3〜24文字）を超える場合は、`environmentName` / `systemName` を短縮して調整します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## アクセス権（RBAC）方針

- Key Vault は `enableRbacAuthorization=true` を前提とします。
- アクセス権（ロール割り当て）は、デプロイ後に Azure Portal から運用者が設定する方針とします。
- そのため、本設計では RBAC のロール割り当てリソースは含めません。

## Private Endpoint

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | pep-kv-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| プライベートリンク接続名 | pep-kv-[common.environmentName]-[common.systemName] | properties.privateLinkServiceConnections.name |
| プライベートリンク対象ID | id(kv-[common.environmentName]-[common.systemName]) | properties.privateLinkServiceConnections.properties.privateLinkServiceId |
| グループID | vault | properties.privateLinkServiceConnections.properties.groupIds |
| サブネットID | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet | properties.subnet.id |

## NSG（PrivateEndpointSubnet）方針

- Key Vault Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で `privatelink.vaultcore.azure.net` を作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | privatelink.vaultcore.azure.net | name |
| 場所 | global | location |

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 親 | pep-kv-[common.environmentName]-[common.systemName] | parent |
| 名前 | dnszg-kv-[common.environmentName]-[common.systemName] | name |
| プライベートDNSゾーン構成名 | privatelink-vaultcore-azure-net | properties.privateDnsZoneConfigs.name |
| プライベートDNSゾーンID | id(privatelink.vaultcore.azure.net) | properties.privateDnsZoneConfigs.properties.privateDnsZoneId |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 親 | privatelink.vaultcore.azure.net | parent |
| 名前 | link-kv-to-vnet-[common.environmentName]-[common.systemName] | name |
| 場所 | global | location |
| 自動登録 | false | properties.registrationEnabled |
| 仮想ネットワークID | id(vnet-[common.environmentName]-[common.systemName]) | properties.virtualNetwork.id |
