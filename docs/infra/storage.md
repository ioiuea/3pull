# Storage Account

## Storage Account 本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | `st[common.environmentName][common.systemName]` | `name` |
| 場所 | `[common.location]` | `location` |
| SKU | `Standard_LRS` | `sku.name` |
| Kind | `StorageV2` | `kind` |
| Access Tier | `Hot` | `properties.accessTier` |
| Public Network Access | `Disabled` | `properties.publicNetworkAccess` |

## 初期 Blob コンテナ

| 用途 | コンテナ名 |
| --- | --- |
| 非同期ジョブ成果物 | `async-jobs` |

## RBAC（Workload Identity）

対象リソースのデプロイが有効で、必要な Managed Identity が Azure 上に存在する場合に Bicep で付与。

| principal | ロール | 付与スコープ | 用途 |
| --- | --- | --- | --- |
| `mi-[env]-[system]-api` | `Storage Blob Data Contributor` | Storage Account | API の作成/更新/参照 |
| `mi-[env]-[system]-worker` | `Storage Blob Data Contributor` | Storage Account | worker の作成/更新/参照 |
| `mi-[env]-[system]-cleanup` | `Storage Blob Data Contributor` | Storage Account | cleanup の削除含むメンテ |

補足:

- スコープはコンテナ単位ではなく Storage Account 固定。
- keda-operator MI には Storage RBAC を付与しません。

## Private Endpoint / DNS

4サービス（blob/file/queue/table）分を作成します。

- PEP: `pep-st-blob|file|queue|table-[env]-[system]`
- DNS Zone:
  - `privatelink.blob.core.windows.net`
  - `privatelink.file.core.windows.net`
  - `privatelink.queue.core.windows.net`
  - `privatelink.table.core.windows.net`
- `network.enableCentralizedPrivateDns=true` の場合は環境側 DNS 作成をスキップ

## データ保護

| 項目 | 設定値 |
| --- | --- |
| Blob soft delete | 有効 |
| Container soft delete | 有効 |
| Blob versioning | 有効 |

## 診断設定 / ロック

- 診断設定: Blob/File/Queue/Table 各サービスを Log Analytics へ送信
- `enableResourceLock=true` の場合に Storage/PEP/DNS へ削除ロック

## 実装ファイル

- `infra/bicep/main.storage.bicep`
- `infra/scripts/generate-storage-params.py`
- `infra/config/storage.json`
