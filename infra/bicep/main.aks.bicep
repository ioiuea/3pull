targetScope = 'resourceGroup'

@description('環境名')
param environmentName string

@description('システム名称')
param systemName string

@description('デプロイ先リージョン')
param location string

@description('モジュール名')
param modulesName string = 'svc'

@description('ロック')
param lockKind string = 'CanNotDelete'

@description('ログアナリティクス名')
param logAnalyticsName string

@description('ログアナリティクスのリソースグループ名')
param logAnalyticsResourceGroupName string

@description('AKS クラスター名')
param aksName string

@description('DNS prefix')
param dnsPrefix string

@description('RBAC 有効化')
param enableRbac bool = true

@description('VNET 名')
param vnetName string

@description('VNET を配置したリソースグループ名')
param vnetResourceGroupName string

@description('Application Gateway 名')
param applicationGatewayName string

@description('Application Gateway を配置したリソースグループ名')
param applicationGatewayResourceGroupName string

@description('System node pool 名')
param agentPoolName string = 'agentpool'

@description('System node pool VM サイズ')
param agentPoolVmSize string = 'standard_d2s_v4'

@description('System node pool OS ディスクサイズ(GB)')
param agentPoolOsDiskSizeGB int = 0

@description('System node pool 可用性ゾーン')
param agentPoolAvailabilityZones array = [
  '1'
  '2'
  '3'
]

@description('System node pool OS タイプ')
param agentPoolOsType string = 'Linux'

@description('System node pool モード')
param agentPoolMode string = 'System'

@description('System node pool ノード数')
param agentPoolCount int = 3

@description('System node pool 最小ノード数')
param agentPoolMinCount int = 3

@description('System node pool 最大ノード数')
param agentPoolMaxCount int = 6

@description('System node pool 自動スケーリング')
param agentPoolEnableAutoScaling bool = true

@description('User node pool 名')
param userPoolName string = 'userpool'

@description('User node pool VM サイズ')
param userPoolVmSize string

@description('User node pool OS ディスクサイズ(GB)')
param userPoolOsDiskSizeGB int = 0

@description('User node pool 可用性ゾーン')
param userPoolAvailabilityZones array = [
  '1'
  '2'
  '3'
]

@description('User node pool OS タイプ')
param userPoolOsType string = 'Linux'

@description('User node pool モード')
param userPoolMode string = 'User'

@description('User node pool ノード数')
param userPoolCount int

@description('User node pool 最小ノード数')
param userPoolMinCount int

@description('User node pool 最大ノード数')
param userPoolMaxCount int

@description('User node pool 自動スケーリング')
param userPoolEnableAutoScaling bool = true

@description('User node pool ラベル値')
param userPoolLabel string

@description('Network plugin')
param networkPlugin string = 'azure'

@description('Network policy')
param networkPolicy string = 'azure'

@description('Network plugin mode')
param networkPluginMode string = 'overlay'

@description('Load balancer SKU')
param loadBalancerSku string = 'standard'

@description('Pod CIDR')
param podCidr string

@description('Service CIDR')
param serviceCidr string

@description('DNS service IP')
param dnsServiceIP string

@description('自動アップグレードチャンネル')
param autoUpgradeChannel string = 'patch'

@description('Azure Policy addon 有効化')
param enableAzurePolicyAddon bool = true

@description('Ingress Application Gateway addon 有効化')
param enableIngressApplicationGatewayAddon bool = true

@description('AAD Azure RBAC 有効化')
param enableAzureRbac bool = true

@description('マネージド AAD 有効化')
param managedAad bool = true

@description('プライベートクラスター有効化')
param enablePrivateCluster bool = true

@description('プライベートクラスター公開 FQDN 有効化')
param enablePrivateClusterPublicFqdn bool = false

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

var agentSubnetId = resourceId(vnetResourceGroupName, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'AgentNodeSubnet')
var userSubnetId = resourceId(vnetResourceGroupName, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'UserNodeSubnet')
var applicationGatewayId = resourceId(applicationGatewayResourceGroupName, 'Microsoft.Network/applicationGateways', applicationGatewayName)

resource aks 'Microsoft.ContainerService/managedClusters@2024-05-01' = {
  name: aksName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  tags: modulesTags
  properties: {
    dnsPrefix: dnsPrefix
    enableRBAC: enableRbac
    agentPoolProfiles: [
      {
        name: agentPoolName
        vmSize: agentPoolVmSize
        osDiskSizeGB: agentPoolOsDiskSizeGB
        availabilityZones: agentPoolAvailabilityZones
        osType: agentPoolOsType
        mode: agentPoolMode
        count: agentPoolCount
        enableAutoScaling: agentPoolEnableAutoScaling
        minCount: agentPoolMinCount
        maxCount: agentPoolMaxCount
        type: 'VirtualMachineScaleSets'
        vnetSubnetID: agentSubnetId
      }
      {
        name: userPoolName
        vmSize: userPoolVmSize
        osDiskSizeGB: userPoolOsDiskSizeGB
        availabilityZones: userPoolAvailabilityZones
        osType: userPoolOsType
        mode: userPoolMode
        count: userPoolCount
        enableAutoScaling: userPoolEnableAutoScaling
        minCount: userPoolMinCount
        maxCount: userPoolMaxCount
        type: 'VirtualMachineScaleSets'
        vnetSubnetID: userSubnetId
        nodeLabels: {
          pool: userPoolLabel
        }
      }
    ]
    addonProfiles: {
      azurepolicy: {
        enabled: enableAzurePolicyAddon
      }
      ingressApplicationGateway: enableIngressApplicationGatewayAddon ? {
        enabled: true
        config: {
          applicationGatewayId: applicationGatewayId
        }
      } : {
        enabled: false
      }
    }
    aadProfile: {
      enableAzureRBAC: enableAzureRbac
      managed: managedAad
    }
    networkProfile: {
      networkPlugin: networkPlugin
      networkPolicy: networkPolicy
      networkPluginMode: networkPluginMode
      loadBalancerSku: loadBalancerSku
      podCidr: podCidr
      serviceCidr: serviceCidr
      dnsServiceIP: dnsServiceIP
    }
    autoUpgradeProfile: {
      upgradeChannel: autoUpgradeChannel
    }
    apiServerAccessProfile: {
      enablePrivateCluster: enablePrivateCluster
      enablePrivateClusterPublicFQDN: enablePrivateClusterPublicFqdn
    }
  }
}

resource aksDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${aksName}'
  scope: aks
  properties: {
    level: lockKind
  }
}

resource aksDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: aks
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'kube-apiserver'
        enabled: true
      }
      {
        category: 'kube-audit'
        enabled: true
      }
      {
        category: 'kube-audit-admin'
        enabled: true
      }
      {
        category: 'kube-controller-manager'
        enabled: true
      }
      {
        category: 'kube-scheduler'
        enabled: true
      }
      {
        category: 'cluster-autoscaler'
        enabled: true
      }
      {
        category: 'cloud-controller-manager'
        enabled: true
      }
      {
        category: 'guard'
        enabled: true
      }
      {
        category: 'csi-azuredisk-controller'
        enabled: true
      }
      {
        category: 'csi-azurefile-controller'
        enabled: true
      }
      {
        category: 'csi-snapshot-controller'
        enabled: true
      }
      {
        category: 'fleet-member-agent'
        enabled: true
      }
      {
        category: 'fleet-member-net-controller-manager'
        enabled: true
      }
      {
        category: 'fleet-mcs-controller-manager'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

output aksNameOutput string = aks.name
output aksIdOutput string = aks.id
