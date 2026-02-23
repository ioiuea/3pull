# Azure Cosmos DB（NoSQL API）

## Cosmos DB アカウント本体

| 項目                           | 設定値                                                          | Bicepプロパティ名                                    |
| ------------------------------ | --------------------------------------------------------------- | ---------------------------------------------------- |
| 名前                           | cosno-[common.environmentName]-[common.systemName]              | name                                                 |
| 場所                           | [common.location]                                               | location                                             |
| API 種別                       | NoSQL (SQL API)                                                 | kind / properties.capabilities                       |
| SKU                            | Standard                                                        | properties.databaseAccountOfferType                  |
| パブリックアクセス             | Disabled                                                        | properties.publicNetworkAccess                       |
| 自動フェールオーバー           | [cosno.enableAutomaticFailover]（デフォルト: false）            | properties.enableAutomaticFailover                   |
| 複数リージョン書き込み         | [cosno.enableMultipleWriteLocations]（デフォルト: false）       | properties.enableMultipleWriteLocations              |
| セカンダリリージョン           | [cosno.failoverRegions]（デフォルト: `[]`）                     | properties.locations                                 |
| 整合性レベル                   | [cosno.consistencyLevel]（デフォルト: Session）                 | properties.consistencyPolicy.defaultConsistencyLevel |
| ローカル認証無効化             | [cosno.disableLocalAuth]（デフォルト: false）                   | properties.disableLocalAuth                          |
| キーベースメタデータ書込無効化 | [cosno.disableKeyBasedMetadataWriteAccess]（デフォルト: false） | properties.disableKeyBasedMetadataWriteAccess        |

## 診断設定

- 診断設定は有効化します（`allLogs` / `AllMetrics`）。
- 実装時は、利用するリソースプロバイダーでサポートされるカテゴリに合わせて設定します。

## 削除ロック

- Cosmos アカウント / Private Endpoint / Private DNS ゾーンに削除ロックを適用します。

## リソース命名規則

- CAF 準拠の省略形を利用します。
  - `Microsoft.DocumentDB/databaseAccounts`（Cosmos DB account for NoSQL）: `cosno`
  - `Microsoft.DocumentDB/databaseAccounts/sqlDatabases`（NoSQL API の DB 論理リソース）: `cosmos`
- そのため、アカウント名は `cosno-[common.environmentName]-[common.systemName]` を基本とします。
- 文字数制約（3〜44文字）を超える場合は `environmentName` / `systemName` を短縮して調整します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## データベース名 / コンテナ名（論理リソース）

この設計では、Cosmos DB アカウントに加えて **SQL Database は IaC で作成** します。  
一方、コンテナはアプリ要件（パーティションキー、TTL、インデックス設計）に依存するため、
**IaC 対象外** としてデプロイ後に作成します。

| 項目               | 設定方針                                         |
| ------------------ | ------------------------------------------------ |
| データベース名     | `common.systemName` を利用して IaC で作成        |
| コンテナ名         | デプロイ後に運用者が作成                         |
| パーティションキー | コンテナ作成時にアプリ要件で設定                 |
| スループット       | `cosno.throughputMode` などを利用して IaC で設定 |

### バックアップポリシー設定（`infra/common.parameter.json`）

`cosno` オブジェクトで、バックアップ方式と保持条件を利用者が変更できるようにします。

| 項目                                           | 設定値（デフォルト） | 説明                                                                                      |
| ---------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------- |
| `cosno.throughputMode`                         | `Serverless`         | スループット方式（`Manual` / `Autoscale` / `Serverless`）                                 |
| `cosno.manualThroughputRu`                     | `400`                | `Manual` 時の RU/s                                                                        |
| `cosno.autoscaleMaxThroughputRu`               | `1000`               | `Autoscale` 時の最大 RU/s                                                                 |
| `cosno.backupPolicyType`                       | `Periodic`           | バックアップ方式。`Periodic` または `Continuous`                                          |
| `cosno.periodicBackupIntervalInMinutes`        | `240`                | `Periodic` 時のバックアップ間隔（分）                                                     |
| `cosno.periodicBackupRetentionIntervalInHours` | `8`                  | `Periodic` 時の保持時間（時間）                                                           |
| `cosno.periodicBackupStorageRedundancy`        | `Geo`                | `Periodic` 時のバックアップ保存先冗長性（`Geo` / `Local` / `Zone`）                       |
| `cosno.continuousBackupTier`                   | `Continuous30Days`   | `Continuous` 時の保持ティア（`Continuous7Days` / `Continuous30Days`）                     |
| `cosno.failoverRegions`                        | `[]`                 | DR 用セカンダリリージョン一覧（優先順）                                                   |
| `cosno.enableAutomaticFailover`                | `false`              | 自動フェールオーバー有効化                                                                |
| `cosno.enableMultipleWriteLocations`           | `false`              | 複数リージョン書き込み有効化                                                              |
| `cosno.consistencyLevel`                       | `Session`            | 既定整合性（`Strong` / `BoundedStaleness` / `Session` / `ConsistentPrefix` / `Eventual`） |
| `cosno.disableLocalAuth`                       | `false`              | ローカル認証（キー/SAS）無効化                                                            |
| `cosno.disableKeyBasedMetadataWriteAccess`     | `false`              | キーベースのメタデータ書き込み無効化                                                      |

補足:

- `backupPolicyType=Periodic` の場合は `periodic*` パラメータを利用します。
- `backupPolicyType=Continuous` の場合は `continuousBackupTier` を利用します。
- 単一リージョン運用は `failoverRegions=[]`（デフォルト）です。
- `throughputMode=Manual` の場合は `manualThroughputRu` を利用します。
- `throughputMode=Autoscale` の場合は `autoscaleMaxThroughputRu` を利用します。
- `throughputMode=Serverless` の場合は RU/s パラメータを利用しません。

## 認証・アクセス方針

- 本番用途ではキー直接配布を避け、Managed Identity + RBAC を優先します。
- `cosno.disableLocalAuth` でローカル認証（キー/SAS）を制御します（デフォルト: `false`）。
- `cosno.disableKeyBasedMetadataWriteAccess` でキーベースのメタデータ更新可否を制御します（デフォルト: `false`）。
- Data Plane RBAC（Cosmos DB Built-in Data Reader/Contributor など）の具体的なロール割り当ては **IaC 対象外** とし、デプロイ後に Azure Portal で設定します。

## キー管理方式

- 本設計では **MMK（Microsoft-managed key）を前提** とします。
- そのため、Cosmos DB 側で `keyVaultKeyUri` は設定しません。
- CMK（Customer-managed key）は本設計の対象外とし、将来要件が出た場合に別途設計します。

## ネットワーク方針

- `publicNetworkAccess=Disabled` を前提とし、Private Endpoint 経由で接続します。
- Private Endpoint は `PrivateEndpointSubnet` に配置します。
- `docs/infra/network.md` の NSG/UDR 方針に従います。

## Private Endpoint

| 項目                     | 設定値                                                                  | Bicepプロパティ名                                                        |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 名前                     | pep-cosno-[common.environmentName]-[common.systemName]                  | name                                                                     |
| 場所                     | [common.location]                                                       | location                                                                 |
| プライベートリンク接続名 | pep-cosno-[common.environmentName]-[common.systemName]                  | properties.privateLinkServiceConnections.name                            |
| プライベートリンク対象ID | id(cosno-[common.environmentName]-[common.systemName])                  | properties.privateLinkServiceConnections.properties.privateLinkServiceId |
| グループID               | Sql                                                                     | properties.privateLinkServiceConnections.properties.groupIds             |
| サブネットID             | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet | properties.subnet.id                                                     |

## NSG（PrivateEndpointSubnet）方針

- Cosmos DB Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 宛先ポートは `443/TCP` を許可対象とします。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で `privatelink.documents.azure.com` を作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| 項目 | 設定値                          | Bicepプロパティ名 |
| ---- | ------------------------------- | ----------------- |
| 名前 | privatelink.documents.azure.com | name              |
| 場所 | global                          | location          |

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| 項目                        | 設定値                                                   | Bicepプロパティ名                                            |
| --------------------------- | -------------------------------------------------------- | ------------------------------------------------------------ |
| 親                          | pep-cosno-[common.environmentName]-[common.systemName]   | parent                                                       |
| 名前                        | dnszg-cosno-[common.environmentName]-[common.systemName] | name                                                         |
| プライベートDNSゾーン構成名 | privatelink-documents-azure-com                          | properties.privateDnsZoneConfigs.name                        |
| プライベートDNSゾーンID     | id(privatelink.documents.azure.com)                      | properties.privateDnsZoneConfigs.properties.privateDnsZoneId |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| 項目               | 設定値                                                          | Bicepプロパティ名              |
| ------------------ | --------------------------------------------------------------- | ------------------------------ |
| 親                 | privatelink.documents.azure.com                                 | parent                         |
| 名前               | link-cosno-to-vnet-[common.environmentName]-[common.systemName] | name                           |
| 場所               | global                                                          | location                       |
| 自動登録           | false                                                           | properties.registrationEnabled |
| 仮想ネットワークID | id(vnet-[common.environmentName]-[common.systemName])           | properties.virtualNetwork.id   |
