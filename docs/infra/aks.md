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

## Workload Identity 構成責務（現実装）

| 対象 | ServiceAccount 作成 | annotation 設定 | federated credential 作成 |
| --- | --- | --- | --- |
| API / worker / cleanup | backend Helm chart | backend Helm chart (`azure.workload.identity/client-id`) | Bicep (`main.federated-credential.bicep`) |
| AGIC standard / lowlatency | `infra/main.sh` の AGIC Helm | `infra/main.sh` の AGIC Helm `--set serviceAccount.annotations...` | Bicep (`main.federated-credential.bicep`) |
| KEDA operator | `infra/main.sh` の KEDA Helm | `infra/main.sh` の KEDA Helm `--set serviceAccount.operator.annotations...` | Bicep (`main.federated-credential.bicep`) |

## AGIC / KEDA コントローラ導入

`infra/main.sh` の post-deploy で実施します。

- AGIC: `resourceToggles.agicController=true` かつ `resourceToggles.federatedCredential=true` のとき実行
- KEDA: `resourceToggles.kedaController=true` かつ `resourceToggles.federatedCredential=true` のとき実行

## 診断設定 / ロック

- AKS 診断設定: `kube-*` ログ群 + `AllMetrics` を Log Analytics へ送信
- AKS 本体に削除ロックを適用（`enableResourceLock=true` の場合）
