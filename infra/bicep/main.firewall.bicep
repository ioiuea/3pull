targetScope = 'resourceGroup'

@description('環境名')
param environmentName string

@description('システム名称')
param systemName string

@description('デプロイ先リージョン')
param location string

@description('モジュール名')
param modulesName string = 'nw'

@description('ロック')
param lockKind string = 'CanNotDelete'

@description('ログアナリティクス名')
param logAnalyticsName string

@description('ログアナリティクスのリソースグループ名')
param logAnalyticsResourceGroupName string

@description('VNETの名称')
param vnetName string

@description('Firewall IDS/IPS 有効化')
param enableFirewallIdps bool

@description('外向き経路の next hop IP（未指定時はこの Firewall を利用）')
param egressNextHopIp string = ''

@description('AKS ノードサブネットの CIDR（egressNextHopIp 未指定時に Firewall ポリシーで許可）')
param aksEgressSourceAddressPrefixes array = []

@description('Public IP 名')
param publicIPName string

@description('Firewall Policy 名')
param firewallPolicyName string

@description('既存 Firewall Policy を利用し、Policy の作成/更新をスキップするか')
param skipFirewallPolicyDeployment bool = false

@description('Firewall 名')
param firewallName string

@description('IP構成名')
param ipConfigurationName string = 'ipconfig'

@description('Public IP SKU')
param publicIPSku string = 'Standard'

@description('Public IP 割り当て')
param publicIPAllocationMethod string = 'Static'

@description('Public IP バージョン')
param publicIPAddressVersion string = 'IPv4'

@description('DDOS保護モード')
param protectionMode string = 'Enabled'

@description('threat intel mode')
param threatIntelMode string = 'Deny'

@description('intrusion detection mode')
param intrusionDetectionMode string = 'Alert'

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource firewallSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  name: '${vnetName}/AzureFirewallSubnet'
}

resource publicIP 'Microsoft.Network/publicIPAddresses@2022-07-01' = {
  name: publicIPName
  location: location
  tags: modulesTags
  sku: {
    name: publicIPSku
  }
  properties: {
    publicIPAllocationMethod: publicIPAllocationMethod
    publicIPAddressVersion: publicIPAddressVersion
    ddosSettings: {
      protectionMode: protectionMode
    }
  }
}

resource publicIPDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: publicIP
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: []
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
        timeGrain: 'PT1M'
      }
    ]
  }
}

resource publicIPDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${publicIPName}'
  scope: publicIP
  properties: {
    level: lockKind
  }
}

resource existingFirewallPolicy 'Microsoft.Network/firewallPolicies@2024-07-01' existing = if (skipFirewallPolicyDeployment) {
  name: firewallPolicyName
}

resource firewallPolicy 'Microsoft.Network/firewallPolicies@2024-07-01' = if (!skipFirewallPolicyDeployment) {
  name: firewallPolicyName
  tags: modulesTags
  location: location
  properties: {
    threatIntelMode: threatIntelMode
    sku: {
      tier: enableFirewallIdps ? 'Premium' : 'Standard'
    }
    intrusionDetection: enableFirewallIdps ? {
      mode: intrusionDetectionMode
    } : null
  }
}

resource firewallPolicyDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (!skipFirewallPolicyDeployment && lockKind != '') {
  name: 'del-lock-${firewallPolicyName}'
  scope: firewallPolicy
  properties: {
    level: lockKind
  }
}

resource aksEgressRuleCollectionGroup 'Microsoft.Network/firewallPolicies/ruleCollectionGroups@2024-07-01' = if (!skipFirewallPolicyDeployment && empty(egressNextHopIp) && length(aksEgressSourceAddressPrefixes) > 0) {
  parent: firewallPolicy
  name: 'rcg-aks-egress'
  properties: {
    priority: 100
    ruleCollections: [
      {
        name: 'allow-aks-egress'
        priority: 100
        ruleCollectionType: 'FirewallPolicyFilterRuleCollection'
        action: {
          type: 'Allow'
        }
        rules: [
          {
            ruleType: 'NetworkRule'
            name: 'allow-aks-egress-any'
            ipProtocols: [
              'Any'
            ]
            sourceAddresses: [
              ...aksEgressSourceAddressPrefixes
            ]
            destinationAddresses: [
              '*'
            ]
            destinationPorts: [
              '*'
            ]
          }
        ]
      }
    ]
  }
}

resource firewall 'Microsoft.Network/azureFirewalls@2020-11-01' = {
  name: firewallName
  location: location
  tags: modulesTags
  properties: {
    firewallPolicy: {
      id: skipFirewallPolicyDeployment ? existingFirewallPolicy.id : firewallPolicy.id
    }
    ipConfigurations: [
      {
        name: ipConfigurationName
        properties: {
          subnet: {
            id: firewallSubnet.id
          }
          publicIPAddress: {
            id: publicIP.id
          }
        }
      }
    ]
    sku: {
      tier: enableFirewallIdps ? 'Premium' : 'Standard'
    }
  }
}

resource firewallDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${firewallName}'
  scope: firewall
  properties: {
    level: lockKind
  }
}

resource firewallDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: firewall
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
    metrics: [
      {
        category: 'allMetrics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
  }
}

output firewallPrivateIp string = firewall.properties.ipConfigurations[0].properties.privateIPAddress
