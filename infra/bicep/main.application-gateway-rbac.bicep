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

@description('Virtual Network 名')
param virtualNetworkName string

@description('通常系 Application Gateway サブネット名')
param standardApplicationGatewaySubnetName string = 'ApplicationGatewaySubnet'

@description('低遅延系 Application Gateway サブネット名')
param lowLatencyApplicationGatewaySubnetName string = 'ApplicationGatewayLowLatencySubnet'

@description('低遅延系 Application Gateway サブネット有効化')
param enableLowLatencyApplicationGatewaySubnet bool = false

@description('Application Gateway への付与ロール定義 ID')
param appGatewayContributorRoleDefinitionId string = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

@description('Subnet への付与ロール定義 ID')
param networkContributorRoleDefinitionId string = '4d97b98b-1d4f-4787-a291-c67834d212e7'

resource standardApplicationGateway 'Microsoft.Network/applicationGateways@2024-07-01' existing = {
  name: standardApplicationGatewayName
}

resource lowLatencyApplicationGateway 'Microsoft.Network/applicationGateways@2024-07-01' existing = if (enableLowLatencyApplicationGatewaySubnet) {
  name: lowLatencyApplicationGatewayName
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  name: virtualNetworkName
}

resource standardApplicationGatewaySubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: standardApplicationGatewaySubnetName
}

resource lowLatencyApplicationGatewaySubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = if (enableLowLatencyApplicationGatewaySubnet) {
  parent: virtualNetwork
  name: lowLatencyApplicationGatewaySubnetName
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

resource networkContributorForStandardAgicSubnet 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(standardApplicationGatewaySubnet.id, agicStandardManagedIdentity.id, 'NetworkContributor')
  scope: standardApplicationGatewaySubnet
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      networkContributorRoleDefinitionId
    )
    principalId: agicStandardManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource networkContributorForLowLatencyAgicSubnet 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableLowLatencyApplicationGatewaySubnet) {
  name: guid(lowLatencyApplicationGatewaySubnet.id, agicLowLatencyManagedIdentity.id, 'NetworkContributor')
  scope: lowLatencyApplicationGatewaySubnet
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      networkContributorRoleDefinitionId
    )
    principalId: agicLowLatencyManagedIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output standardApplicationGatewayNameOutput string = standardApplicationGateway.name
output agicStandardManagedIdentityNameOutput string = agicStandardManagedIdentity.name
output lowLatencyApplicationGatewayNameOutput string = enableLowLatencyApplicationGatewaySubnet ? lowLatencyApplicationGateway!.name : ''
output agicLowLatencyManagedIdentityNameOutput string = enableLowLatencyApplicationGatewaySubnet ? agicLowLatencyManagedIdentity!.name : ''
