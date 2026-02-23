# Azure Container Registry

## ACR 本体

| 項目                 | 設定値                                         | Bicepプロパティ名                   |
| -------------------- | ---------------------------------------------- | ----------------------------------- |
| 名前                 | cr[common.environmentName][common.systemName] | name                                |
| 場所                 | [common.location]                              | location                            |
| SKU Name             | Premium                                        | sku.name                            |
| パブリックアクセス   | Disabled                                       | properties.publicNetworkAccess      |
| ネットワークバイパス | AzureServices                                  | properties.networkRuleBypassOptions |

## 診断設定

- 対象: ACR 本体（`Microsoft.ContainerRegistry/registries`）
- ログ: `audit`, `allLogs`
- メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- ACR 本体に削除ロックを適用
- Private Endpoint に削除ロックを適用
- Private DNS ゾーンに削除ロックを適用（`network.enableCentralizedPrivateDns=false` の場合のみ）

## リソース命名規則

- CAF の省略形ルールに準拠し、Container Registry は `cr` を利用します。
- ACR 名は **ハイフン不可** です。
- ACR 名は英小文字・数字のみを使用します。
- そのため命名は `cr[common.environmentName][common.systemName]` を基本とします。
- 文字数制約（5〜50文字）を超える場合は、`environmentName` / `systemName` を短縮して調整します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## Private Endpoint

| 項目                     | 設定値                                                                  | Bicepプロパティ名                                                        |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 名前                     | pep-cr-[common.environmentName]-[common.systemName]                    | name                                                                     |
| 場所                     | [common.location]                                                       | location                                                                 |
| プライベートリンク接続名 | pep-cr-[common.environmentName]-[common.systemName]                    | properties.privateLinkServiceConnections.name                            |
| プライベートリンク対象ID | id(cr[common.environmentName][common.systemName])                      | properties.privateLinkServiceConnections.properties.privateLinkServiceId |
| グループID               | registry                                                                | properties.privateLinkServiceConnections.properties.groupIds             |
| サブネットID             | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet | properties.subnet.id                                                     |

## NSG（PrivateEndpointSubnet）方針

- ACR Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で `privatelink.azurecr.io` を作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| 項目 | 設定値                 | Bicepプロパティ名 |
| ---- | ---------------------- | ----------------- |
| 名前 | privatelink.azurecr.io | name              |
| 場所 | global                 | location          |

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| 項目                        | 設定値                                                 | Bicepプロパティ名                                            |
| --------------------------- | ------------------------------------------------------ | ------------------------------------------------------------ |
| 親                          | pep-cr-[common.environmentName]-[common.systemName]   | parent                                                       |
| 名前                        | dnszg-cr-[common.environmentName]-[common.systemName] | name                                                         |
| プライベートDNSゾーン構成名 | privatelink-azurecr-io                                 | properties.privateDnsZoneConfigs.name                        |
| プライベートDNSゾーンID     | id(privatelink.azurecr.io)                             | properties.privateDnsZoneConfigs.properties.privateDnsZoneId |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| 項目               | 設定値                                                    | Bicepプロパティ名              |
| ------------------ | --------------------------------------------------------- | ------------------------------ |
| 親                 | privatelink.azurecr.io                                    | parent                         |
| 名前               | link-acr-to-vnet-[common.environmentName]-[common.systemName] | name                           |
| 場所               | global                                                    | location                       |
| 自動登録           | false                                                     | properties.registrationEnabled |
| 仮想ネットワークID | id(vnet-[common.environmentName]-[common.systemName])     | properties.virtualNetwork.id   |
