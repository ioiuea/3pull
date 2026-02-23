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

@description('ingestionモード')
param applicationInsightsIngestion string = 'LogAnalytics'

@description('アプリケーションインサイトの種類')
param applicationInsightsType string = 'web'

@description('ログアナリティクスのリソースグループ名')
param logAnalyticsResourceGroupName string

@description('ログアナリティクス名')
param logAnalyticsName string

@description('アプリケーションインサイト名')
param applicationInsightsName string

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: modulesTags
  kind: applicationInsightsType
  properties: {
    Application_Type: applicationInsightsType
    WorkspaceResourceId: resourceId(
      logAnalyticsResourceGroupName,
      'Microsoft.OperationalInsights/workspaces',
      logAnalyticsName
    )
    RetentionInDays: retentionInDays
    IngestionMode: applicationInsightsIngestion
    publicNetworkAccessForIngestion: publicNetworkAccessForIngestion
    publicNetworkAccessForQuery: publicNetworkAccessForQuery
  }
}

resource deleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${applicationInsightsName}'
  scope: applicationInsights
  properties: {
    level: lockKind
  }
}

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: applicationInsights
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

output resourceGroupName string = resourceGroup().name
output applicationInsightsScope object = applicationInsights
