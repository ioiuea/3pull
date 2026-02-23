# Azure Database for PostgreSQL Flexible Server

## PostgreSQL Flexible Server 本体

| 項目                           | 設定値                                                                          | Bicepプロパティ名                                    |
| ------------------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 名前                           | psql-[common.environmentName]-[common.systemName]                               | name                                                 |
| 場所                           | [common.location]                                                               | location                                             |
| バージョン                     | 16 (例)                                                                         | properties.version                                   |
| 価格レベル                     | [postgres.skuTier]（デフォルト: Burstable）                                     | sku.tier                                             |
| コンピューティングサイズ       | [postgres.skuName]（デフォルト: Standard_B2s）                                  | sku.name                                             |
| 性能目安（デフォルト）         | 2 vCore / 4 GiB メモリ / 最大 IOPS 1280                                         | SKU仕様による                                        |
| ストレージサイズ               | [postgres.storageSizeGB] GiB（デフォルト: 32）                                  | properties.storage.storageSizeGB                     |
| ストレージ自動拡張             | [postgres.enableStorageAutoGrow]（デフォルト: false）                           | properties.storage.autoGrow                          |
| バックアップ保持日数           | [postgres.backupRetentionDays]                                                  | properties.backup.backupRetentionDays                |
| Geo冗長バックアップ            | [postgres.enableGeoRedundantBackup] (`true`/`false`)                            | properties.backup.geoRedundantBackup                 |
| ゾーン冗長 HA                  | [postgres.enableZoneRedundantHa] (`true`/`false`)                               | properties.highAvailability.mode                     |
| スタンバイAZ                   | [要件に応じて設定]                                                              | properties.highAvailability.standbyAvailabilityZone  |
| カスタムメンテナンスウィンドウ | [postgres.enableCustomMaintenanceWindow] (`true`/`false`)                       | properties.maintenanceWindow.customWindow            |
| メンテナンス曜日               | [postgres.maintenanceWindow.dayOfWeek]                                          | properties.maintenanceWindow.dayOfWeek               |
| メンテナンス開始時（UTC）      | [postgres.maintenanceWindow.startHour]:[postgres.maintenanceWindow.startMinute] | properties.maintenanceWindow.startHour / startMinute |
| パブリックアクセス             | Disabled                                                                        | properties.network.publicNetworkAccess               |

## 診断設定

- 診断設定は有効化します（`allLogs` / `AllMetrics`）。
- 実装時は、利用するリソースプロバイダーでサポートされるカテゴリに合わせて設定します。

## 削除ロック

- サーバー / Private Endpoint / Private DNS ゾーンに削除ロックを適用します。

## 高可用性（HA）設定

- `infra/common.parameter.json` の `postgres.enableZoneRedundantHa` で制御します。
  - `true`: `highAvailability.mode = ZoneRedundant`
  - `false`（デフォルト）: `highAvailability.mode = Disabled`
- `true` の場合は、リージョン/AZのサポート可否とコスト影響を事前に確認します。

### バックアップ設定

- `infra/common.parameter.json` の `postgres.backupRetentionDays` で PITR 保持日数を指定します（`7`〜`35`、デフォルト `7`）。
- `infra/common.parameter.json` の `postgres.enableGeoRedundantBackup` で Geo 冗長バックアップの有効/無効を指定します（デフォルト `false`）。

### メンテナンスウィンドウ設定

- `infra/common.parameter.json` の `postgres.enableCustomMaintenanceWindow` でカスタム指定の有効/無効を制御します。
  - `false`（デフォルト）: システム管理スケジュール
  - `true`: `postgres.maintenanceWindow` の値で固定化
- `postgres.maintenanceWindow.dayOfWeek` / `startHour` / `startMinute` を指定します（UTC）。

### SKU / ストレージ設定

- `infra/common.parameter.json` の `postgres.skuTier` で価格レベルを指定します（デフォルト `Burstable`）。
- `infra/common.parameter.json` の `postgres.skuName` でコンピューティングサイズを指定します（デフォルト `Standard_B2s`）。
- `infra/common.parameter.json` の `postgres.storageSizeGB` でストレージ容量を指定します（デフォルト `32` GiB）。
- `infra/common.parameter.json` の `postgres.enableStorageAutoGrow` でストレージ自動拡張の有効/無効を指定します（デフォルト `false`）。

## リソース命名規則

- CAF の省略形ルールに準拠し、PostgreSQL は `psql` を利用します。
- そのため命名は `psql-[common.environmentName]-[common.systemName]` を基本とします。
- 文字数制約（3〜63文字）を超える場合は、`environmentName` / `systemName` を短縮して調整します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## 認証・アクセス方針

- 認証方式は **併用（Microsoft Entra 認証 + パスワード認証）** を採用します。
- AKS 上のアプリ（Next.js / FastAPI）からの通常接続は、原則として Entra 認証（Workload Identity / Managed Identity）を利用します。
- パスワード認証は、移行期間や障害時オペレーション（break-glass）向けの補助経路として残します。
- スキーマ責務に合わせて、接続主体と権限を分離します。
  - Next.js（`auth` スキーマ）用の DB ロール
  - FastAPI（`core` スキーマ）用の DB ロール
- アプリ接続ユーザー/ロールの作成・権限付与は、デプロイ後の初期化手順で実施します。

### IaC 実装時の入力方法

- `resourceToggles.postgresDatabase=true` の場合のみ PostgreSQL をデプロイします。
- 管理者パスワードは `common.parameter.json` に保持せず、`main.sh` 実行時に `POSTGRES_ADMIN_PASSWORD` 環境変数で注入します。

## データベース / スキーマ作成方針

- 本設計では、PostgreSQL Flexible Server 本体までを IaC 対象とします。
- データベース、スキーマ、テーブル、ロール/権限設定は **IaC 対象外** とし、
  デプロイ後に運用手順（SQL 実行・マイグレーション）で作成します。
- 既存のアプリ実装方針（Drizzle / Alembic など）に合わせて、スキーマ管理責務を分離します。

## ネットワーク方針

- `publicNetworkAccess=Disabled` を前提とし、Private Endpoint 経由で接続します。
- Private Endpoint は `PrivateEndpointSubnet` に配置します。
- `docs/infra/network.md` の NSG/UDR 方針に従います。

## Private Endpoint

| 項目                     | 設定値                                                                  | Bicepプロパティ名                                                        |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 名前                     | pep-psql-[common.environmentName]-[common.systemName]                   | name                                                                     |
| 場所                     | [common.location]                                                       | location                                                                 |
| プライベートリンク接続名 | pep-psql-[common.environmentName]-[common.systemName]                   | properties.privateLinkServiceConnections.name                            |
| プライベートリンク対象ID | id(psql-[common.environmentName]-[common.systemName])                   | properties.privateLinkServiceConnections.properties.privateLinkServiceId |
| グループID               | postgresqlServer                                                        | properties.privateLinkServiceConnections.properties.groupIds             |
| サブネットID             | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet | properties.subnet.id                                                     |

## NSG（PrivateEndpointSubnet）方針

- PostgreSQL Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 宛先ポートは `5432/TCP` を許可対象とします。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で `privatelink.postgres.database.azure.com` を作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| 項目 | 設定値                                  | Bicepプロパティ名 |
| ---- | --------------------------------------- | ----------------- |
| 名前 | privatelink.postgres.database.azure.com | name              |
| 場所 | global                                  | location          |

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| 項目                        | 設定値                                                  | Bicepプロパティ名                                            |
| --------------------------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| 親                          | pep-psql-[common.environmentName]-[common.systemName]   | parent                                                       |
| 名前                        | dnszg-psql-[common.environmentName]-[common.systemName] | name                                                         |
| プライベートDNSゾーン構成名 | privatelink-postgres-database-azure-com                 | properties.privateDnsZoneConfigs.name                        |
| プライベートDNSゾーンID     | id(privatelink.postgres.database.azure.com)             | properties.privateDnsZoneConfigs.properties.privateDnsZoneId |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| 項目               | 設定値                                                         | Bicepプロパティ名              |
| ------------------ | -------------------------------------------------------------- | ------------------------------ |
| 親                 | privatelink.postgres.database.azure.com                        | parent                         |
| 名前               | link-psql-to-vnet-[common.environmentName]-[common.systemName] | name                           |
| 場所               | global                                                         | location                       |
| 自動登録           | false                                                          | properties.registrationEnabled |
| 仮想ネットワークID | id(vnet-[common.environmentName]-[common.systemName])          | properties.virtualNetwork.id   |

## 未確定項目（実装前に決定）

- Entra 管理者に割り当てる主体（ユーザー / グループ / サービスプリンシパル）
- break-glass 用パスワード認証の運用ルール（保管先、ローテーション手順、利用手順）
