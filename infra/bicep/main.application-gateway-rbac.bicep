targetScope = 'resourceGroup'

@description('Managed Identity を配置したリソースグループ名')
param managedIdentityResourceGroupName string

@description('通常系 AGIC 用 Managed Identity 名')
param agicStandardManagedIdentityName string

@description('低遅延系 AGIC 用 Managed Identity 名')
param agicLowLatencyManagedIdentityName string = ''

@description('通常系 Application Gateway 名')
param standardApplicationGatewayName string

@description('低遅延系 Application Gateway 名')
param lowLatencyApplicationGatewayName string = ''

@description('低遅延系 Application Gateway サブネット有効化')
param enableLowLatencyApplicationGatewaySubnet bool = false

@description('Application Gateway への付与ロール定義 ID')
param appGatewayContributorRoleDefinitionId string = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

resource standardApplicationGateway 'Microsoft.Network/applicationGateways@2024-07-01' existing = {
  name: standardApplicationGatewayName
}

resource lowLatencyApplicationGateway 'Microsoft.Network/applicationGateways@2024-07-01' existing = if (enableLowLatencyApplicationGatewaySubnet) {
  name: lowLatencyApplicationGatewayName
}

resource agicStandardManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: agicStandardManagedIdentityName
}

resource agicLowLatencyManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = if (enableLowLatencyApplicationGatewaySubnet) {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: agicLowLatencyManagedIdentityName
}

resource appGatewayContributorForStandardAgic 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(standardApplicationGateway.id, agicStandardManagedIdentity.id, 'AppGatewayContributor')
  scope: standardApplicationGateway
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      appGatewayContributorRoleDefinitionId
    )
    principalId: agicStandardManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource appGatewayContributorForLowLatencyAgic 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableLowLatencyApplicationGatewaySubnet) {
  name: guid(lowLatencyApplicationGateway.id, agicLowLatencyManagedIdentity.id, 'AppGatewayContributor')
  scope: lowLatencyApplicationGateway
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      appGatewayContributorRoleDefinitionId
    )
    principalId: agicLowLatencyManagedIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output standardApplicationGatewayNameOutput string = standardApplicationGateway.name
output agicStandardManagedIdentityNameOutput string = agicStandardManagedIdentity.name
output lowLatencyApplicationGatewayNameOutput string = enableLowLatencyApplicationGatewaySubnet ? lowLatencyApplicationGateway!.name : ''
output agicLowLatencyManagedIdentityNameOutput string = enableLowLatencyApplicationGatewaySubnet ? agicLowLatencyManagedIdentity!.name : ''
