# Managed Identity

## 目的

AKS 上の workload（API / worker / cleanup）および KEDA が、接続文字列を使わずに Azure リソースへアクセスできるようにするため、User Assigned Managed Identity を定義する。

## 命名規則

| 種別 | 命名規則 |
| --- | --- |
| API 用 | `mi-[common.environmentName]-[common.systemName]-api` |
| worker 用 | `mi-[common.environmentName]-[common.systemName]-worker` |
| cleanup 用 | `mi-[common.environmentName]-[common.systemName]-cleanup` |

例: `common.environmentName=dev`, `common.systemName=3pull`

- `mi-dev-3pull-api`
- `mi-dev-3pull-worker`
- `mi-dev-3pull-cleanup`

## 役割

| Managed Identity | 主な用途 |
| --- | --- |
| API 用 | Service Bus 送信、Blob 読み取り、Key Vault 読み取り |
| worker 用 | Service Bus 受信、Blob 読み書き、Key Vault 読み取り |
| cleanup 用 | Blob 削除、Key Vault 読み取り |

## 実装方針

- AKS デプロイ時に Bicep で同時作成する。
- 作成定義は `infra/bicep/main.aks.bicep` で管理する。
- 生成された `clientId` / `principalId` は後続の以下で利用する。
  - Kubernetes `ServiceAccount` annotation (`azure.workload.identity/client-id`)
  - Azure RBAC 付与
  - federated credential 作成

## 関連ドキュメント

- AKS 設計: [docs/infra/aks.md](./aks.md)
- Service Bus 設計: [docs/infra/service-bus.md](./service-bus.md)
- Kubernetes 配備手順: [docs/kubernetes-task.md](../kubernetes-task.md)
