# ストレージアカウント

## ストレージアカウント本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | st[common.environmentName][common.systemName] | name |
| 場所 | [common.location] | location |
| SKU Name | Standard_LRS | sku.name |
| Kind | StorageV2 | kind |
| Access Tier | Hot | properties.accessTier |
| パブリックアクセス | Disabled | properties.publicNetworkAccess |

## 診断設定

- 対象:
  - Blob Service（`Microsoft.Storage/storageAccounts/blobServices`）
  - File Service（`Microsoft.Storage/storageAccounts/fileServices`）
  - Queue Service（`Microsoft.Storage/storageAccounts/queueServices`）
  - Table Service（`Microsoft.Storage/storageAccounts/tableServices`）
- ログ（各サービス共通）: `audit`, `allLogs`
- メトリック（各サービス共通）: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- Storage Account 本体に削除ロックを適用
- 各 Private Endpoint（blob/file/queue/table）に削除ロックを適用
- 各 Private DNS ゾーンに削除ロックを適用（`network.enableCentralizedPrivateDns=false` の場合のみ）

## Blob サービスのデータ保護

誤削除や上書き時の復旧性を高めるため、以下を有効化します。

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| BLOB の論理的な削除 | 有効 | blobServices.properties.deleteRetentionPolicy.enabled |
| BLOB の論理削除保持日数 | 7日 | blobServices.properties.deleteRetentionPolicy.days |
| コンテナーの論理的な削除 | 有効 | blobServices.properties.containerDeleteRetentionPolicy.enabled |
| コンテナー論理削除保持日数 | 7日 | blobServices.properties.containerDeleteRetentionPolicy.days |
| バージョン管理 | 有効 | blobServices.properties.isVersioningEnabled |

## リソース命名規則

- CAF の省略形ルールに準拠し、Storage Account は `st` を利用します。
- Storage Account 名は **ハイフン不可** です。
- Storage Account 名は英小文字・数字のみを使用します。
- そのため命名は `st[common.environmentName][common.systemName]` を基本とします。
- 文字数制約（3〜24文字）を超える場合は、`environmentName` / `systemName` を短縮して調整します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## コンテナ

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | st[common.environmentName][common.systemName]/default/[common.systemName] | name |
| パブリックアクセス | None | properties.publicAccess |

## Private Endpoint

| サービス | 名前 | プライベートリンク接続名 | グループID | サブネットID |
| --- | --- | --- | --- | --- |
| Blob | pep-st-blob-[common.environmentName]-[common.systemName] | pep-st-blob-[common.environmentName]-[common.systemName] | blob | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet |
| File | pep-st-file-[common.environmentName]-[common.systemName] | pep-st-file-[common.environmentName]-[common.systemName] | file | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet |
| Queue | pep-st-queue-[common.environmentName]-[common.systemName] | pep-st-queue-[common.environmentName]-[common.systemName] | queue | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet |
| Table | pep-st-table-[common.environmentName]-[common.systemName] | pep-st-table-[common.environmentName]-[common.systemName] | table | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet |

共通:

- 場所: `[common.location]`
- プライベートリンク対象ID: `id(st[common.environmentName][common.systemName])`
- Bicepプロパティ:
  - `name`
  - `properties.privateLinkServiceConnections.name`
  - `properties.privateLinkServiceConnections.properties.privateLinkServiceId`
  - `properties.privateLinkServiceConnections.properties.groupIds`
  - `properties.subnet.id`

## NSG（PrivateEndpointSubnet）方針

- Blob Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で各サービスの Private DNS ゾーンを作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| サービス | ゾーン名 |
| --- | --- |
| Blob | privatelink.blob.core.windows.net |
| File | privatelink.file.core.windows.net |
| Queue | privatelink.queue.core.windows.net |
| Table | privatelink.table.core.windows.net |

Bicepプロパティ:

- `name`
- `location` (`global`)

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 各サービス分を作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| サービス | 親 (Private Endpoint) | DNS ゾーングループ名 | DNS ゾーン構成名 | DNS ゾーンID |
| --- | --- | --- | --- | --- |
| Blob | pep-st-blob-[common.environmentName]-[common.systemName] | dnszg-st-blob-[common.environmentName]-[common.systemName] | privatelink-st-blob-core-windows-net | id(privatelink.blob.core.windows.net) |
| File | pep-st-file-[common.environmentName]-[common.systemName] | dnszg-st-file-[common.environmentName]-[common.systemName] | privatelink-file-core-windows-net | id(privatelink.file.core.windows.net) |
| Queue | pep-st-queue-[common.environmentName]-[common.systemName] | dnszg-st-queue-[common.environmentName]-[common.systemName] | privatelink-queue-core-windows-net | id(privatelink.queue.core.windows.net) |
| Table | pep-st-table-[common.environmentName]-[common.systemName] | dnszg-st-table-[common.environmentName]-[common.systemName] | privatelink-table-core-windows-net | id(privatelink.table.core.windows.net) |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| サービス | 親 (Private DNS ゾーン) | リンク名 |
| --- | --- | --- |
| Blob | privatelink.blob.core.windows.net | link-st-blob-to-vnet-[common.environmentName]-[common.systemName] |
| File | privatelink.file.core.windows.net | link-st-file-to-vnet-[common.environmentName]-[common.systemName] |
| Queue | privatelink.queue.core.windows.net | link-st-queue-to-vnet-[common.environmentName]-[common.systemName] |
| Table | privatelink.table.core.windows.net | link-st-table-to-vnet-[common.environmentName]-[common.systemName] |

共通:

- 場所: `global`
- 自動登録: `false` (`properties.registrationEnabled`)
- 仮想ネットワークID: `id(vnet-[common.environmentName]-[common.systemName])` (`properties.virtualNetwork.id`)
