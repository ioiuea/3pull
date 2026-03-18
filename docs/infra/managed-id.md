# Managed Identity

## 目的

AKS 上の workload とコントローラ（AGIC/KEDA）が、接続文字列を使わず Azure リソースへアクセスするために User Assigned Managed Identity を利用します。

## 命名規則

| 用途 | 命名規則 |
| --- | --- |
| API | `mi-[common.environmentName]-[common.systemName]-api` |
| worker | `mi-[common.environmentName]-[common.systemName]-worker` |
| schedulers | `mi-[common.environmentName]-[common.systemName]-schedulers` |
| migration | `mi-[common.environmentName]-[common.systemName]-migration` |
| keda-operator | `mi-[common.environmentName]-[common.systemName]-keda-operator` |
| AGIC通常系 | `mi-[common.environmentName]-[common.systemName]-agic-standard` |
| AGIC低遅延系 | `mi-[common.environmentName]-[common.systemName]-agic-lowlatency`（低遅延オプション有効時） |

## 作成タイミング

- `infra/bicep/main.managed-ids.bicep` で作成
- デプロイ順は `Managed IDs -> Application Gateway -> Application Gateway RBAC -> AKS`

## RBAC 方針（最小権限）

| Managed Identity | Key Vault | Service Bus | Storage | App Gateway |
| --- | --- | --- | --- | --- |
| API | Secrets User, Crypto User | Data Sender | Blob Data Contributor | - |
| worker | Secrets User, Crypto User | Data Receiver | Blob Data Contributor | - |
| schedulers | Secrets User | - | Blob Data Contributor | - |
| migration | Secrets User | - | - | - |
| keda-operator | - | Data Receiver | - | - |
| agic-standard | - | - | - | AppGateway Contributor（通常系） |
| agic-lowlatency | - | - | - | AppGateway Contributor（低遅延系） |

補足:

- keda-operator MI は Service Bus の監視用途に限定し、Key Vault/Storage 権限は付与しません。
- AGIC MI は App Gateway 更新専用です。
- migration MI は maint-vm 上で Azure SQL bootstrap / Alembic 実行に利用します。
- API / worker MI は、Key Vault Secret 参照に加えて Azure SQL Always Encrypted で Azure Key Vault のキーを利用するため `Crypto User` を付与します。
- migration MI の主目的は Azure SQL 接続時の Entra principal であり、AKS workload identity 用ではありません。
- migration MI の Azure RBAC は、DB 接続設定を Key Vault から取得するための `Secrets User` を基本とします。Azure SQL 内の DDL 権限は DB user 作成後に別途付与します。
- migration MI は maint-vm に単独で割り当てる前提とし、maint-vm の SystemAssigned は利用しません。

## ServiceAccount / Federated Credential との対応

- アプリ SA（`sa-[env]-[system]-api|worker|schedulers`）は backend Helm で作成
- AGIC/KEDA SA（`sa-agic-standard`, `sa-agic-lowlatency`, `keda-operator`）は `infra/main.sh` の Helm で作成
- federated credential は `infra/bicep/main.federated-credential.bicep` で一括作成

補足:

- migration MI は maint-vm に割り当てるため、Kubernetes ServiceAccount や federated credential の対象外です。

## 関連

- AKS: [aks.md](./aks.md)
- App Gateway: [agw.md](./agw.md)
- Azure SQL Database: [azure-sql-database.md](./azure-sql-database.md)
- メンテナンスVM: [maint-vm.md](./maint-vm.md)
- Service Bus: [service-bus.md](./service-bus.md)
- Storage: [storage.md](./storage.md)
- Key Vault: [kv.md](./kv.md)
