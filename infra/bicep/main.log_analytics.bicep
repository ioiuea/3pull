targetScope = 'resourceGroup'

@description('環境名')
param environmentName string

@description('システム名称')
param systemName string

@description('デプロイ先リージョン')
param location string

@description('モジュール名')
param modulesName string = 'monitor'

@description('データ保持期間')
param retentionInDays int = 365

@description('Ingestion用のパブリックネットワークアクセス')
param publicNetworkAccessForIngestion string = 'Disabled'

@description('クエリ用のパブリックネットワークアクセス')
param publicNetworkAccessForQuery string = 'Enabled'

@description('ロック')
param lockKind string = 'CanNotDelete'

@description('sku')
param logAnalyticsSku string = 'PerGB2018'

@description('ログアナリティクス名')
param logAnalyticsName string

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: logAnalyticsName
  location: location
  tags: modulesTags
  properties: {
    sku: {
      name: logAnalyticsSku
    }
    retentionInDays: retentionInDays
    publicNetworkAccessForIngestion: publicNetworkAccessForIngestion
    publicNetworkAccessForQuery: publicNetworkAccessForQuery
  }
}

resource deleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${logAnalyticsName}'
  scope: logAnalytics
  properties: {
    level: lockKind
  }
}

output resourceGroupName string = resourceGroup().name
output logAnalyticsScope object = logAnalytics
