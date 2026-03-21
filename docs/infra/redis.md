# Azure Managed Redis

## Azure Managed Redis 本体

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | `redis-[common.environmentName]-[common.systemName]` | `name` |
| 場所 | `[common.location]` | `location` |
| SKU | `infra/config/redis-managed.json` の既定値 + `infra/common.parameter.json.redis` の上書き | 実装時に確定 |
| Public Network Access | `Disabled` | 実装時に確定 |
| 最小 TLS | `1.2` | 実装時に確定 |
| 認証方式 | `Microsoft Entra` | 実装時に確定 |
| Access Key 認証 | `無効` | 実装時に確定 |
| 接続先 FQDN | `<cacheName>.<region>.redis.azure.net` | 実装時に確定 |
| 接続ポート | `10000` | 実装時に確定 |

補足:

- リソース名は CAF の省略形ルールに従い、`redis` を利用します。
- 命名は `redis-[common.environmentName]-[common.systemName]` を基本とします。
- 文字数制約を超える場合は、`environmentName` / `systemName` を短縮して調整します。
- 本ドキュメントは最終形の Azure Managed Redis 構成を記載し、ローカル検証用の一時構成は記載しません。
- `infra/` は Azure Managed Redis のリソース作成から、backend / ops が利用する接続情報出力までを責務に含みます。
- Azure Managed Redis の Entra 認証主体は `user or service principal` と `managed identity` のどちらか一方を選択する前提とします。
- 本番向け IaC では `managed identity` を選択する前提で設計します。

### 設定の責務分担

- `infra/config/redis-managed.json`
  - Redis の固定方針・既定値を持ちます。
  - 例:
    - Public Network Access = `Disabled`
    - Microsoft Entra 認証 = `有効`
    - Access Key 認証 = `無効`
    - 最小 TLS = `1.2`
- `infra/common.parameter.json`
  - 環境差分として必要な項目のみ `redis` object で上書きします。
  - 初期導入では少なくとも以下を上書き対象とします。
    - `skuName`
    - `highAvailabilityEnabled`
  - 補足:
    - `capacity` は `common.parameter.json` では受け取らず、Bicep 側で SKU に応じた既定値を使います。
      - `Enterprise_*` は `2`
      - `EnterpriseFlash_*` は `3`
      - それ以外の SKU は未指定扱いにします。
    - Azure Managed Redis には Azure Cache for Redis の `replicasPerMaster` 概念はそのまま存在しないため、本設計では `highAvailabilityEnabled` に読み替えます。
- `resourceToggles.redis`
  - Redis のデプロイ有無を制御します。

参考:

- Azure CAF Resource Abbreviations
  - https://learn.microsoft.com/ja-jp/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations

## RBAC（Workload Identity）

対象リソースのデプロイが有効で、必要な Managed Identity が Azure 上に存在する場合に付与します。

| principal | ロール | スコープ | 用途 |
| --- | --- | --- | --- |
| `mi-[env]-[system]-api` | `default` Access Policy | Azure Managed Redis | backend API のレート制限用接続 |
| `mi-[env]-[system]-redis-ops` | `default` Access Policy | Azure Managed Redis | maint-vm からの block key 確認・解除 |

補足:

- 初期導入では `api` と `redis-ops` の Managed Identity を対象とします。
- `worker` / `schedulers` は現時点では Redis 利用前提に含めません。
- Azure Managed Redis では、接続主体を `Redis user` として追加し、Access Policy を割り当てます。
- 初期導入では backend API / redis-ops が read/write を行うため、Redis の `default` Access Policy を前提とします。
- 本番向け構成では、Redis 側の接続主体として `managed identity` を選択し、`mi-[env]-[system]-api` を紐づけます。

## Private Endpoint / DNS

- Private Endpoint: `pep-redis-[env]-[system]`
- 配置サブネット: `PrivateEndpointSubnet`
- Private DNS Zone: `privatelink.redis.azure.net`
- `network.enableCentralizedPrivateDns=true` の場合は環境側 DNS 作成をスキップします。
- 接続元制御、NSG、UDR の詳細は `docs/infra/network.md` を正とします。

補足:

- Azure Managed Redis は Private Endpoint 経由で接続する前提とします。
- Public Network Access は本番向け IaC で `Disabled` とし、閉域接続のみを許可します。
- 本番系の接続は AKS からの閉域接続を前提とします。
- クライアント接続先は `privatelink` 側の名前ではなく `<cacheName>.<region>.redis.azure.net:10000` を利用します。

## 診断設定 / ロック

- 診断設定は Log Analytics へ送信します。
- 診断設定は `AllMetrics` のみを有効化します。
- `enableResourceLock=true` の場合に Azure Managed Redis / Private Endpoint / Private DNS へ削除ロックを適用します。

## 実装ファイル

- `infra/bicep/main.redis-managed.bicep`
- `infra/scripts/generate-redis-managed-params.py`
- `infra/config/redis-managed.json`

## 出力連携

- backend Helm values へ、少なくとも以下を出力します。
  - `REDIS_HOST`
  - `REDIS_PORT`
  - `REDIS_SSL`
- backend Helm values 生成では、Redis 接続情報に加えて以下も同じ Phase で出力対象とします。
  - `TRUST_PROXY_HEADERS`
  - `TRUSTED_PROXY_CIDRS`
  - `RATE_LIMIT_MODE`
  - 各 `RATE_LIMIT_POLICY_*`
- `TRUSTED_PROXY_CIDRS` は手入力固定値ではなく、Application Gateway サブネット CIDR から動的生成します。
- App Gateway 二重経路化時は、対象サブネット CIDR をカンマ区切りで連結して出力します。
- ops 用には `scripts/ops/ip-rate-limit/generated.env.sh` を生成し、以下を export します。
  - `REDIS_HOST`
  - `REDIS_PORT`
  - `REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID`
  - `REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID`
