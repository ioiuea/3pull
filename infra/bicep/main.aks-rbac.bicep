targetScope = 'resourceGroup'

@description('Managed Identity を配置したリソースグループ名')
param managedIdentityResourceGroupName string

@description('AKS クラスター名')
param aksName string

@description('AKS Operator 用 Managed Identity 名')
param aksOperatorManagedIdentityName string

@description('AKS Admin 用 Managed Identity 名')
param aksAdminManagedIdentityName string

@description('AKS Cluster User ロール定義 ID')
param aksClusterUserRoleDefinitionId string = '4abbcc35-e782-43d8-92c5-2d3f1bd2253f'

@description('AKS RBAC Reader ロール定義 ID')
param aksRbacReaderRoleDefinitionId string = '7f6c6a51-bcf8-42ba-9220-52d62157d7db'

@description('AKS RBAC Writer ロール定義 ID')
param aksRbacWriterRoleDefinitionId string = 'a7ffa36f-339b-4b5c-8bdf-e2c188b2c0eb'

@description('AKS RBAC Cluster Admin ロール定義 ID')
param aksRbacClusterAdminRoleDefinitionId string = 'b1ff04bb-8a4e-4dc4-8eb5-8693973ce19b'

resource aks 'Microsoft.ContainerService/managedClusters@2024-05-01' existing = {
  name: aksName
}

resource aksOperatorManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: aksOperatorManagedIdentityName
}

resource aksAdminManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: aksAdminManagedIdentityName
}

resource aksClusterUserForOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, aksOperatorManagedIdentity.id, 'AksClusterUser')
  scope: aks
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      aksClusterUserRoleDefinitionId
    )
    principalId: aksOperatorManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aksRbacReaderForOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, aksOperatorManagedIdentity.id, 'AksRbacReader')
  scope: aks
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      aksRbacReaderRoleDefinitionId
    )
    principalId: aksOperatorManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aksRbacWriterForOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, aksOperatorManagedIdentity.id, 'AksRbacWriter')
  scope: aks
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      aksRbacWriterRoleDefinitionId
    )
    principalId: aksOperatorManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aksRbacClusterAdminForAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, aksAdminManagedIdentity.id, 'AksRbacClusterAdmin')
  scope: aks
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      aksRbacClusterAdminRoleDefinitionId
    )
    principalId: aksAdminManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output aksNameOutput string = aks.name
output aksOperatorManagedIdentityNameOutput string = aksOperatorManagedIdentity.name
output aksAdminManagedIdentityNameOutput string = aksAdminManagedIdentity.name
