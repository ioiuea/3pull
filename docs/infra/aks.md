# AzureKubernetesService

- ※[]内は`infra/common.parameter.json`の設定値に従って設定されます。

| AKS名                              | 概要                |
| ---------------------------------- | ------------------- |
| aks-[common.environmentName]-[common.systemName] | アプリデプロイ用AKS |

## 基本

| 項目            | 設定値                                 | Bicepプロパティ名     |
| --------------- | -------------------------------------- | --------------------- |
| 名前            | aks-[common.environmentName]-[common.systemName]     | name                  |
| 場所            | [common.location]                      | location              |
| ID              | SystemAssigned                         | identity.type         |
| DNSプレフィクス | aks-dns-[common.environmentName]-[common.systemName] | properties.dnsPrefix  |
| RBACの有効化    | true                                   | properties.enableRBAC |

## 診断設定

- 対象: AKS クラスター（`Microsoft.ContainerService/managedClusters`）
- ログカテゴリ:
  - `kube-apiserver`
  - `kube-audit`
  - `kube-audit-admin`
  - `kube-controller-manager`
  - `kube-scheduler`
  - `cluster-autoscaler`
  - `cloud-controller-manager`
  - `guard`
  - `csi-azuredisk-controller`
  - `csi-azurefile-controller`
  - `csi-snapshot-controller`
  - `fleet-member-agent`
  - `fleet-member-net-controller-manager`
  - `fleet-mcs-controller-manager`
- メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- AKS クラスター本体に削除ロックを適用

## エージェントプール

| 項目             | 設定値                                                  | Bicepプロパティ名                              |
| ---------------- | ------------------------------------------------------- | ---------------------------------------------- |
| 名前             | agentpool                                               | properties.agentPoolProfiles.name              |
| OSディスクサイズ | 0                                                       | properties.agentPoolProfiles.osDiskSizeGB      |
| VMサイズ         | standard_d2s_v4                                         | properties.agentPoolProfiles.vmSize            |
| 可用性ゾーン     | 1,2,3                                                   | properties.agentPoolProfiles.avalavilityZones  |
| OSタイプ         | Linux                                                   | properties.agentPoolProfiles.osType            |
| モード           | System                                                  | properties.agentPoolProfiles.mode              |
| カウント         | 3                                                       | properties.agentPoolProfiles.count             |
| 最小VM数         | 3                                                       | properties.agentPoolProfiles.minCount          |
| 最大VM数         | 6                                                       | properties.agentPoolProfiles.maxCount          |
| 自動スケーリング | true                                                    | properties.agentPoolProfiles.enableAutoScaling |
| サブネットID     | id(vnet-[common.environmentName]-[common.systemName]/AgentNodeSubnet) | properties.agentPoolProfiles.vnetSubnetID      |

## ユーザープール

| 項目             | 設定値                                                 | Bicepプロパティ名                              |
| ---------------- | ------------------------------------------------------ | ---------------------------------------------- |
| 名前             | userpool                                               | properties.agentPoolProfiles.name              |
| OSディスクサイズ | 0                                                      | properties.agentPoolProfiles.osDiskSizeGB      |
| VMサイズ         | [aks.userPoolVmSize]                                   | properties.agentPoolProfiles.vmSize            |
| 可用性ゾーン     | 1,2,3                                                  | properties.agentPoolProfiles.avalavilityZones  |
| OSタイプ         | Linux                                                  | properties.agentPoolProfiles.osType            |
| モード           | User                                                   | properties.agentPoolProfiles.mode              |
| カウント         | [aks.userPoolCount]                                    | properties.agentPoolProfiles.count             |
| 最小VM数         | [aks.userPoolMinCount]                                 | properties.agentPoolProfiles.minCount          |
| 最大VM数         | [aks.userPoolMaxCount]                                 | properties.agentPoolProfiles.maxCount          |
| 自動スケーリング | true                                                   | properties.agentPoolProfiles.enableAutoScaling |
| サブネットID     | id(vnet-[common.environmentName]-[common.systemName]/UserNodeSubnet) | properties.agentPoolProfiles.vnetSubnetID      |
| ラベル           | pool: [aks.userPoolLabel]                              | properties.agentPoolProfiles.nodeLabels        |

## アドオン：Azureポリシー

| 項目   | 設定値 | Bicepプロパティ名                            |
| ------ | ------ | -------------------------------------------- |
| 有効化 | true   | properties.addonProfiles.azurepolicy.enabled |

## アドオン：イングレスコントローラー

| 項目   | 設定値                                      | Bicepプロパティ名                                                              |
| ------ | ------------------------------------------- | ------------------------------------------------------------------------------ |
| 有効化 | true                                        | properties.addonProfiles.ingressApplicationGateway.enabled                     |
| AGWID  | id(agw-[common.environmentName]-[common.systemName]-agic) | properties.addonProfiles.ingressApplicationGateway.config.applicationGatewayId |

## AAD情報

| 項目                  | 設定値 | Bicepプロパティ名                     |
| --------------------- | ------ | ------------------------------------- |
| RBACの有効化          | true   | properties.aadProfile.enableAzureRBAC |
| マネージドAADの有効化 | true   | properties.aadProfile.managed         |

## ネットワーク情報

| 項目                         | 設定値                                      | Bicepプロパティ名                           |
| ---------------------------- | ------------------------------------------- | ------------------------------------------- |
| ネットワークプラグイン       | azure                                       | properties.networkProfile.networkPlugin     |
| ネットワークポリシー         | azure                                       | properties.networkProfile.networkPolicy     |
| ネットワークプラグインモード | overlay                                     | properties.networkProfile.networkPluginMode |
| ロードバランサ―SKU           | standard                                    | properties.networkPraofile.loadBalancerSku  |
| ポッドCIDR                   | [aks.podCidr]                               | properties.networkProfile.podCidr           |
| サービスCIDR                 | [aks.serviceCidr]                           | properties.networkProfile.serviceCidr       |
| DNSサービスIP                | [aks.serviceCidrのレンジの10個目のIP]       | properties.networkProfile.dnsServiceIP      |

※ ポッドCIDRはVNETのIPアドレスレンジとは別空間のため、`infra/common.parameter.json` の `aks.podCidr` で任意指定

## 自動アップグレード情報

| 項目               | 設定値 | Bicepプロパティ名                            |
| ------------------ | ------ | -------------------------------------------- |
| 自動アップグレード | patch  | properties.autoUpgradeProfile.upgradeChannel |

## APIサーバーアクセス情報

| 項目                                               | 設定値 | Bicepプロパティ名                                                |
| -------------------------------------------------- | ------ | ---------------------------------------------------------------- |
| プライベートクラスター有効化                       | true   | properties.apiServerAccessProfile.enablePrivateCluster           |
| プライベートクラスター用追加パブリックFQDNの有効化 | false  | properties.apiServerAccessProfile.enablePrivateClusterPublicFQDN |
