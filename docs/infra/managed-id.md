# Managed Identity

## 目的

AKS 上の workload とコントローラ（AGIC/KEDA）が、接続文字列を使わず Azure リソースへアクセスするために User Assigned Managed Identity を利用します。

## 命名規則

| 用途 | 命名規則 |
| --- | --- |
| API | `mi-[common.environmentName]-[common.systemName]-api` |
| worker | `mi-[common.environmentName]-[common.systemName]-worker` |
| schedulers | `mi-[common.environmentName]-[common.systemName]-schedulers` |
| keda-operator | `mi-[common.environmentName]-[common.systemName]-keda-operator` |
| AGIC通常系 | `mi-[common.environmentName]-[common.systemName]-agic-standard` |
| AGIC低遅延系 | `mi-[common.environmentName]-[common.systemName]-agic-lowlatency`（低遅延オプション有効時） |

## 作成タイミング

- `infra/bicep/main.managed-ids.bicep` で作成
- デプロイ順は `Managed IDs -> Application Gateway -> Application Gateway RBAC -> AKS`

## RBAC 方針（最小権限）

| Managed Identity | Key Vault | Service Bus | Storage | App Gateway |
| --- | --- | --- | --- | --- |
| API | Secrets User | Data Sender | Blob Data Contributor | - |
| worker | Secrets User | Data Receiver | Blob Data Contributor | - |
| schedulers | Secrets User | - | Blob Data Contributor | - |
| keda-operator | - | Data Receiver | - | - |
| agic-standard | - | - | - | AppGateway Contributor（通常系） |
| agic-lowlatency | - | - | - | AppGateway Contributor（低遅延系） |

補足:

- keda-operator MI は Service Bus の監視用途に限定し、Key Vault/Storage 権限は付与しません。
- AGIC MI は App Gateway 更新専用です。

## ServiceAccount / Federated Credential との対応

- アプリ SA（`sa-[env]-[system]-api|worker|schedulers`）は backend Helm で作成
- AGIC/KEDA SA（`sa-agic-standard`, `sa-agic-lowlatency`, `keda-operator`）は `infra/main.sh` の Helm で作成
- federated credential は `infra/bicep/main.federated-credential.bicep` で一括作成

## 関連

- AKS: [aks.md](./aks.md)
- App Gateway: [agw.md](./agw.md)
- Service Bus: [service-bus.md](./service-bus.md)
- Storage: [storage.md](./storage.md)
- Key Vault: [kv.md](./kv.md)
