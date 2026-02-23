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

@description('NSG 定義')
param nsgs array

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource networkSecurityGroups 'Microsoft.Network/networkSecurityGroups@2024-07-01' = [
  for nsg in nsgs: {
    name: 'nsg-${environmentName}-${systemName}-${nsg.subnetName}'
    location: location
    tags: modulesTags
    properties: {
      securityRules: nsg.securityRules
    }
  }
]

resource nsgLocks 'Microsoft.Authorization/locks@2020-05-01' = [
  for (nsg, i) in nsgs: if (lockKind != '') {
    name: 'del-lock-nsg-${environmentName}-${systemName}-${nsg.subnetName}'
    scope: networkSecurityGroups[i]
    properties: {
      level: lockKind
    }
  }
]

resource nsgDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = [
  for (nsg, i) in nsgs: {
    name: 'diagnostic-to-${logAnalyticsName}'
    scope: networkSecurityGroups[i]
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
      metrics: []
    }
  }
]

output nsgNames array = [for nsg in nsgs: 'nsg-${environmentName}-${systemName}-${nsg.subnetName}']
