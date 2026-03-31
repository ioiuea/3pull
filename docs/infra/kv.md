# Key Vault

## Key Vault 本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | `kv-[common.environmentName]-[common.systemName]` | `name` |
| 場所 | `[common.location]` | `location` |
| SKU | `standard` | `properties.sku.name` |
| RBAC 有効化 | `true` | `properties.enableRbacAuthorization` |
| Public Network Access | `Disabled` | `properties.publicNetworkAccess` |
| Soft Delete | `true` | `properties.enableSoftDelete` |
| Purge Protection | `true` | `properties.enablePurgeProtection` |
| 保持日数 | `90` | `properties.softDeleteRetentionInDays` |

## RBAC（Workload Identity）

対象リソースのデプロイが有効で、必要な Managed Identity が Azure 上に存在する場合に Bicep で付与。

| principal | ロール | スコープ | 用途 |
| --- | --- | --- | --- |
| `mi-[env]-[system]-api` | `Key Vault Secrets User`, `Key Vault Crypto User` | Key Vault | API 実行時のSecret参照 / Always Encrypted 用キー参照 |
| `mi-[env]-[system]-worker` | `Key Vault Secrets User`, `Key Vault Crypto User` | Key Vault | worker 実行時のSecret参照 / Always Encrypted 用キー参照 |
| `mi-[env]-[system]-schedulers` | `Key Vault Secrets User` | Key Vault | schedulers 実行時のSecret参照 |
| `mi-[env]-[system]-kv-admin` | `Key Vault Secrets Officer` | Key Vault | maint-vm からの secret 登録 / 更新 |
| bootstrap/CI principal | `Key Vault Secrets Officer` | Key Vault | Secret 登録/更新 |

補足:

- keda-operator MI には Key Vault RBAC を付与しません（最小権限）。
- `Key Vault Crypto User` は Azure SQL Always Encrypted で Azure Key Vault のキーを利用する principal に付与します。
- Secret 値そのものは IaC に含めず、`az keyvault secret set` で投入します。

## Private Endpoint / DNS

- PEP: `pep-kv-[env]-[system]`
- DNS Zone: `privatelink.vaultcore.azure.net`
- `network.enableCentralizedPrivateDns=true` の場合は環境側 DNS 作成をスキップ

## 診断設定 / ロック

- 診断設定: `allLogs`, `audit`, `AllMetrics` -> Log Analytics
- `enableResourceLock=true` の場合に Key Vault/PEP/DNS へ削除ロック

## 実装ファイル

- `infra/bicep/main.key-vault.bicep`
- `infra/scripts/generate-key-vault-params.py`
- `infra/config/key-vault.json`
