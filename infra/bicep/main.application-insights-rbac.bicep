targetScope = 'resourceGroup'

@description('Managed Identity を配置したリソースグループ名')
param managedIdentityResourceGroupName string

@description('Application Insights 名')
param applicationInsightsName string

@description('API 用 Managed Identity 名')
param apiManagedIdentityName string

@description('worker 用 Managed Identity 名')
param workerManagedIdentityName string

@description('schedulers 用 Managed Identity 名')
param schedulersManagedIdentityName string

@description('Application Insights への付与ロール定義 ID')
param monitoringMetricsPublisherRoleDefinitionId string = '3913510d-42f4-4e42-8a64-420c390055eb'

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

resource apiManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: apiManagedIdentityName
}

resource workerManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: workerManagedIdentityName
}

resource schedulersManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: schedulersManagedIdentityName
}

resource monitoringMetricsPublisherForApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(applicationInsights.id, apiManagedIdentity.id, 'MonitoringMetricsPublisher')
  scope: applicationInsights
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      monitoringMetricsPublisherRoleDefinitionId
    )
    principalId: apiManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource monitoringMetricsPublisherForWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(applicationInsights.id, workerManagedIdentity.id, 'MonitoringMetricsPublisher')
  scope: applicationInsights
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      monitoringMetricsPublisherRoleDefinitionId
    )
    principalId: workerManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource monitoringMetricsPublisherForSchedulers 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(applicationInsights.id, schedulersManagedIdentity.id, 'MonitoringMetricsPublisher')
  scope: applicationInsights
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      monitoringMetricsPublisherRoleDefinitionId
    )
    principalId: schedulersManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output applicationInsightsNameOutput string = applicationInsights.name
output apiManagedIdentityNameOutput string = apiManagedIdentity.name
output workerManagedIdentityNameOutput string = workerManagedIdentity.name
output schedulersManagedIdentityNameOutput string = schedulersManagedIdentity.name
