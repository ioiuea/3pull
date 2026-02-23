# Azure Cache for Redis

## Azure Cache for Redis 本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | redis-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| SKU | [redis.skuName]（デフォルト: Basic） | sku.name |
| SKU Family | `redis.skuName` に応じて自動設定（Basic/Standard: C, Premium: P） | sku.family |
| 容量 | [redis.capacity]（デフォルト: 0） | sku.capacity |
| シャード数 | [redis.shardCount]（デフォルト: 1） | properties.shardCount |
| スケール方針 | [redis.scaleStrategy]（デフォルト: vertical） | 運用設計パラメータ |
| ゾーン配置ポリシー | [redis.zonalAllocationPolicy]（デフォルト: Automatic） | properties.zonalAllocationPolicy（Premium のみ） |
| ゾーン指定 | [redis.zones]（デフォルト: `[]`） | zones |
| レプリカ数 | [redis.replicasPerMaster]（デフォルト: 1） | properties.replicasPerMaster（Premium のみ） |
| Geo レプリケーション | [redis.enableGeoReplication]（デフォルト: false） | 将来拡張パラメータ（現時点は情報保持のみ） |
| TLS 最小バージョン | 1.2 | properties.minimumTlsVersion |
| 非 TLS ポート | false | properties.enableNonSslPort |
| パブリックアクセス | Disabled | properties.publicNetworkAccess |

- `redis.skuName` の選択肢: `Basic` / `Standard` / `Premium`
- `sku.family` は `redis.skuName` から自動決定
  - `Basic` / `Standard`: `C`
  - `Premium`: `P`
- `redis.capacity` の範囲:
  - `Basic` / `Standard`: `0`〜`6`
  - `Premium`: `1`〜`6`
- `redis.zonalAllocationPolicy`:
  - `Automatic`（Basic / Standard はこの値で固定運用）
  - `NoZones`
  - `UserDefined`（Premium のみ）
- `redis.zones`:
  - `redis.zonalAllocationPolicy=UserDefined` の場合のみ指定
  - `"1"` / `"2"` / `"3"` の配列
  - Premium のみ利用可能
- `redis.skuName` が `Basic` / `Standard` の場合、Premium 専用パラメータ（`shardCount` / `replicasPerMaster` / `zonalAllocationPolicy` / `zones` / `enableRdbBackup` 系）は指定しても無視されます。
- `redis.enableGeoReplication=true` の場合:
  - `redis.skuName=Premium` が必要
  - `redis.replicasPerMaster=1` を前提

## 診断設定

- 診断設定は有効化します。
  - ログ: `allLogs`, `audit`
  - メトリック: `AllMetrics`

## 削除ロック

- Redis / Private Endpoint / Private DNS ゾーンに削除ロックを適用します。

## リソース命名規則

- CAF の省略形ルールに準拠し、Azure Cache for Redis は `redis` を利用します。
- そのため命名は `redis-[common.environmentName]-[common.systemName]` を基本とします。
- 文字数制約（1〜63文字）を超える場合は、`environmentName` / `systemName` を短縮して調整します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## 認証・アクセス方針

- 基本方針は Microsoft Entra 認証と Access Key 認証の併用です。
- `infra/common.parameter.json` の `redis.enableMicrosoftEntraAuthentication` で Entra 認証の有効/無効を制御します。
  - `true`（デフォルト）: Entra 認証有効
  - `false`: Entra 認証無効
- `infra/common.parameter.json` の `redis.disableAccessKeyAuthentication` で Access Key 認証の無効化を選択できます。
  - `false`（デフォルト）: Entra + Access Key 併用
  - `true`: Access Key 無効化（Entra のみ）
- `redis.disableAccessKeyAuthentication=true` を指定する場合は、`redis.enableMicrosoftEntraAuthentication=true` が必要です。
- アプリ接続は `6380/TLS` を前提とします（非 TLS ポートは無効）。
- Entra の具体的なロール割り当て主体（Managed Identity / グループ）は、アプリ要件に依存するため IaC 対象外とし、構築後に Azure Portal で設定します。

## データ構成作成方針

- 本設計では、Azure Cache for Redis 本体までを IaC 対象とします。
- キー設計、TTL 設計、名前空間設計、アプリ側キャッシュ戦略は **IaC 対象外** とし、
  デプロイ後にアプリ実装・運用設計で管理します。

## デプロイ対象制御

- `infra/common.parameter.json` の `resourceToggles.redis=true` の場合のみデプロイします。

## ネットワーク方針

- `publicNetworkAccess=Disabled` を前提とし、Private Endpoint 経由で接続します。
- Private Endpoint は `PrivateEndpointSubnet` に配置します。
- `docs/infra/network.md` の NSG/UDR 方針に従います。

## Private Endpoint

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | pep-redis-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| プライベートリンク接続名 | pep-redis-[common.environmentName]-[common.systemName] | properties.privateLinkServiceConnections.name |
| プライベートリンク対象ID | id(redis-[common.environmentName]-[common.systemName]) | properties.privateLinkServiceConnections.properties.privateLinkServiceId |
| グループID | redisCache | properties.privateLinkServiceConnections.properties.groupIds |
| サブネットID | vnet-[common.environmentName]-[common.systemName]/PrivateEndpointSubnet | properties.subnet.id |

## NSG（PrivateEndpointSubnet）方針

- Redis Private Endpoint 宛ては AKS サブネットからのみ許可します。
- 許可ソースは `UserNodeSubnet` と `AgentNodeSubnet` の両方です。
- 宛先ポートは `6380/TCP` を許可対象とします。
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` に従います。

## 運用時の接続元方針

- 接続元制御は `PrivateEndpointSubnet` に適用する NSG で実施します。
- デフォルト方針として、Redis Private Endpoint への接続元は以下を許可します。
  - `UserNodeSubnet`
  - `AgentNodeSubnet`
  - `MaintenanceSubnet`
- 受信規則は `docs/infra/network.md` の `nsg-[common.environmentName]-[common.systemName]-pep` を正として管理します。
- 追加の接続元要件がある場合は、同 NSG の受信規則を拡張して対応します。

## Private DNS ゾーン

`network.enableCentralizedPrivateDns` を使って、ゾーン作成の有無を制御します。

- `false`（デフォルト）: 集約 DNS なし。環境内で `privatelink.redis.cache.windows.net` を作成して利用
- `true`: 集約 DNS あり。環境内でのゾーン作成はスキップし、集約側 DNS（ハブ側）で管理されたゾーンを利用

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | privatelink.redis.cache.windows.net | name |
| 場所 | global | location |

## DNS ゾーングループ

PEP と Private DNS ゾーンを紐づけるリソース。

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、DNS ゾーングループも作成しません

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 親 | pep-redis-[common.environmentName]-[common.systemName] | parent |
| 名前 | dnszg-redis-[common.environmentName]-[common.systemName] | name |
| プライベートDNSゾーン構成名 | privatelink-redis-cache-windows-net | properties.privateDnsZoneConfigs.name |
| プライベートDNSゾーンID | id(privatelink.redis.cache.windows.net) | properties.privateDnsZoneConfigs.properties.privateDnsZoneId |

## 仮想ネットワークリンク

- `network.enableCentralizedPrivateDns=false` の場合: 作成します
- `network.enableCentralizedPrivateDns=true` の場合: 環境内ゾーンを作成しないため、仮想ネットワークリンクも作成しません

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 親 | privatelink.redis.cache.windows.net | parent |
| 名前 | link-redis-to-vnet-[common.environmentName]-[common.systemName] | name |
| 場所 | global | location |
| 自動登録 | false | properties.registrationEnabled |
| 仮想ネットワークID | id(vnet-[common.environmentName]-[common.systemName]) | properties.virtualNetwork.id |

## 可用性設定

### メンテナンスウィンドウ設定

- デフォルト: 未設定（Azure システム管理スケジュール）
- `infra/common.parameter.json` の `redis.enableCustomMaintenanceWindow=false` でシステム管理を利用
- `redis.enableCustomMaintenanceWindow=true` の場合は、`redis.maintenanceWindow` を使って固定化
  - `dayOfWeek`: `0`〜`6`（曜日）
  - `startHour`: `0`〜`23`（UTC）
  - `duration`: ISO 8601 形式（例: `PT5H`）

### バックアップ設定

- デフォルト: RDB バックアップ無効（Azure 既定）
- `redis.enableRdbBackup=false` でバックアップ無効のまま利用
- `redis.enableRdbBackup=true` の場合は、以下を設定
  - `redis.rdbBackupFrequencyInMinutes`: `15/30/60/360/720/1440`
  - `redis.rdbBackupMaxSnapshotCount`: `1` 以上
  - `redis.rdbStorageConnectionString`: バックアップ保存先のストレージ接続文字列（必須）
