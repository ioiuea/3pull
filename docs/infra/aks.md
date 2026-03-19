# Azure Kubernetes Service

- ※ `[]` 内は `infra/common.parameter.json` の設定値に従います。

## クラスター基本

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| 名前 | `aks-[common.environmentName]-[common.systemName]` | `name` |
| 場所 | `[common.location]` | `location` |
| ID | `SystemAssigned` | `identity.type` |
| DNSプレフィクス | `aks-dns-[common.environmentName]-[common.systemName]` | `properties.dnsPrefix` |
| RBAC有効化 | `true` | `properties.enableRBAC` |
| プライベートクラスター | `true` | `properties.apiServerAccessProfile.enablePrivateCluster` |
| プライベートFQDN公開 | `false` | `properties.apiServerAccessProfile.enablePrivateClusterPublicFQDN` |

## OIDC / Workload Identity

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| OIDC issuer 有効化 | `true` | `properties.oidcIssuerProfile.enabled` |
| Workload Identity 有効化 | `true` | `properties.securityProfile.workloadIdentity.enabled` |

## ネットワーク

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| Network Plugin | `azure` | `properties.networkProfile.networkPlugin` |
| Network Policy | `azure` | `properties.networkProfile.networkPolicy` |
| Network Plugin Mode | `overlay` | `properties.networkProfile.networkPluginMode` |
| Load Balancer SKU | `standard` | `properties.networkProfile.loadBalancerSku` |
| Pod CIDR | `[aks.podCidr]` | `properties.networkProfile.podCidr` |
| Service CIDR | `[aks.serviceCidr]` | `properties.networkProfile.serviceCidr` |
| DNS Service IP | `[aks.serviceCidr の先頭 +10]` | `properties.networkProfile.dnsServiceIP` |

## アドオン

| 項目 | 設定値 | 備考 |
| --- | --- | --- |
| Azure Policy | `true` | 有効化済み |
| Key Vault Secrets Provider (CSI) | `true` | 有効化済み |
| AGIC addon | `false` | AGIC は addon 非利用。Helm で導入 |

## ACR アタッチ

| 項目 | 設定値 | 実装 |
| --- | --- | --- |
| ACR Pull 権限 | `cr[env][system]` へ `AcrPull` | `Microsoft.Authorization/roleAssignments` |

## Azure RBAC

`aadProfile.enableAzureRBAC=true` を前提に、AKS への運用アクセスも Azure RBAC で制御します。

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| マネージド AAD | `true` | `properties.aadProfile.managed` |
| Azure RBAC | `true` | `properties.aadProfile.enableAzureRBAC` |

## maint-vm からの AKS 運用アクセス

maint-vm に割り当てた `mi-[common.environmentName]-[common.systemName]-aks-operator` と `mi-[common.environmentName]-[common.systemName]-aks-admin` に対し、用途ごとに以下を付与します。

| Managed Identity | ロール | スコープ | 用途 |
| --- | --- | --- | --- |
| `mi-[env]-[system]-aks-operator` | `Azure Kubernetes Service Cluster User Role` | AKS | `az aks get-credentials` 実行 |
| `mi-[env]-[system]-aks-operator` | `Azure Kubernetes Service RBAC Reader` | AKS | cluster-wide な参照系 `kubectl` 実行 |
| `mi-[env]-[system]-aks-operator` | `Azure Kubernetes Service RBAC Writer` | AKS | アプリ配備や定常運用の更新系 `kubectl` / `helm` 実行 |
| `mi-[env]-[system]-aks-admin` | `Azure Kubernetes Service RBAC Cluster Admin` | AKS | 初期構築・緊急対応の高権限作業 |

補足:

- `aks-operator` は日常運用用であり、`RBAC Reader` と `RBAC Writer` を AKS スコープで付与します。
- namespace は Bicep で事前作成せず、Helm 実行時の `--create-namespace` に任せます。
- `aks-admin` は `RBAC Cluster Admin` により cluster 全体の変更が可能なため、初期構築・AGIC/KEDA 導入・緊急対応に限定して使います。
- `RBAC Cluster Admin` には `listClusterUserCredential/action` が含まれるため、`aks-admin` に `Cluster User Role` は別途付与しません。
- 付与スコープは AKS リソースに限定し、node resource group には直接ロール付与しません。
- 現行実装では app namespace は `infra/config/federated-credential.json` の `appNamespace` で管理しており、値は `application` です。
- backend / frontend Helm chart の namespace は `systemName` から自動生成せず、`Release.Namespace` をそのまま使います。
- アプリ本体は `application` namespace、AGIC は `ingress` namespace、KEDA は `keda` namespace を固定値として扱います。
- Helm 実行引数と federated credential はこの固定値に揃える前提です。

## Workload Identity 構成責務（現実装）

| 対象 | ServiceAccount 作成 | annotation 設定 | federated credential 作成 |
| --- | --- | --- | --- |
| API / worker / schedulers | backend Helm chart | backend Helm chart (`azure.workload.identity/client-id`) | Bicep (`main.federated-credential.bicep`) |
| AGIC standard / lowlatency | `infra/main.sh` の AGIC Helm | `infra/main.sh` の AGIC Helm `--set serviceAccount.annotations...` | Bicep (`main.federated-credential.bicep`) |
| KEDA operator | `infra/main.sh` の KEDA Helm | `infra/main.sh` の KEDA Helm `--set serviceAccount.operator.annotations...` | Bicep (`main.federated-credential.bicep`) |

## AGIC / KEDA コントローラ導入

`infra/main.sh` の post-deploy で実施します。

- AGIC: `resourceToggles.agicController=true` かつ Federated Credential が作成済みのとき実行
- KEDA: `resourceToggles.kedaController=true` かつ Federated Credential が作成済みのとき実行

## 診断設定 / ロック

- AKS 診断設定: `kube-*` ログ群 + `AllMetrics` を Log Analytics へ送信
- AKS 本体に削除ロックを適用（`enableResourceLock=true` の場合）
