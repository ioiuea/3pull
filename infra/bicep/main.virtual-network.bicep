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

@description('VNETのアドレスプレフィックス')
param vnetAddressPrefixes array

@description('VNETのDNSサーバー')
param vnetDnsServers array = []

@description('DDoS Protection を有効化するか')
param enableDdosProtection bool = true

@description('DDoS Protection Plan のリソースID')
param ddosProtectionPlanId string = ''

@description('DDoS Protection Plan 名称')
param ddosProtectionPlanName string

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource ddosProtectionPlan 'Microsoft.Network/ddosProtectionPlans@2024-07-01' = if (enableDdosProtection && empty(ddosProtectionPlanId)) {
  name: ddosProtectionPlanName
  location: location
  tags: modulesTags
}

resource ddosProtectionPlanDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (enableDdosProtection && empty(ddosProtectionPlanId) && lockKind != '') {
  name: 'del-lock-${ddosProtectionPlanName}'
  scope: ddosProtectionPlan
  properties: {
    level: lockKind
  }
}

var ddosProtectionPlanIdEffective = !enableDdosProtection ? '' : (empty(ddosProtectionPlanId) ? ddosProtectionPlan.id : ddosProtectionPlanId)

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' = {
  name: vnetName
  location: location
  tags: modulesTags
  properties: union({
    addressSpace: {
      addressPrefixes: vnetAddressPrefixes
    }
  }, empty(ddosProtectionPlanIdEffective) ? {} : {
    enableDdosProtection: true
    ddosProtectionPlan: {
      id: ddosProtectionPlanIdEffective
    }
  }, empty(vnetDnsServers) ? {} : {
    dhcpOptions: {
      dnsServers: vnetDnsServers
    }
  })
}

resource deleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${vnetName}'
  scope: virtualNetwork
  properties: {
    level: lockKind
  }
}

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: virtualNetwork
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

output virtualNetworkName string = virtualNetwork.name
output virtualNetworkId string = virtualNetwork.id
output ddosProtectionPlanIdOutput string = ddosProtectionPlanIdEffective
