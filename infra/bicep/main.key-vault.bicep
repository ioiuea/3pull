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

@description('VNET 名')
param vnetName string

@description('VNET のリソースグループ名')
param vnetResourceGroupName string

@description('Managed Identity を配置したリソースグループ名')
param managedIdentityResourceGroupName string

@description('API 用 Managed Identity 名')
param apiManagedIdentityName string

@description('worker 用 Managed Identity 名')
param workerManagedIdentityName string

@description('schedulers 用 Managed Identity 名')
param schedulersManagedIdentityName string

@description('Workload Identity 用 RBAC 付与を有効化')
param enableWorkloadIdentityRbac bool = true

@description('Key Vault 名')
param keyVaultName string

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string = 'privatelink.vaultcore.azure.net'

@description('Private DNS ゾーングループ名')
param privateDnsZoneGroupName string

@description('Private DNS 仮想ネットワークリンク名')
param privateDnsVnetLinkName string

@description('Key Vault SKU family')
param keyVaultSkuFamily string = 'A'

@description('Key Vault SKU name')
param keyVaultSkuName string = 'standard'

@description('Key Vault の public network access')
param publicNetworkAccess string = 'Disabled'

@description('RBAC 有効化')
param enableRbacAuthorization bool = true

@description('Soft Delete 有効化')
param enableSoftDelete bool = true

@description('Purge Protection 有効化')
param enablePurgeProtection bool = true

@description('Soft Delete の保持日数')
param softDeleteRetentionInDays int = 90

@description('集約 Private DNS を利用する場合は true')
param enableCentralizedPrivateDns bool = false

@description('Key Vault Secrets Officer を付与する principal object ID（未設定時はスキップ）')
param keyVaultOfficerObjectId string = ''

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

var keyVaultSecretsOfficerRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'
)

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
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

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: modulesTags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: keyVaultSkuFamily
      name: keyVaultSkuName
    }
    enableRbacAuthorization: enableRbacAuthorization
    publicNetworkAccess: publicNetworkAccess
    enableSoftDelete: enableSoftDelete
    enablePurgeProtection: enablePurgeProtection
    softDeleteRetentionInDays: softDeleteRetentionInDays
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
    }
  }
}

resource keyVaultDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${keyVaultName}'
  scope: keyVault
  properties: {
    level: lockKind
  }
}

resource keyVaultDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: keyVault
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
      {
        categoryGroup: 'audit'
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
      }
    ]
  }
}

resource keyVaultSecretsUserForApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableWorkloadIdentityRbac) {
  name: guid(keyVault.id, apiManagedIdentity.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalId: apiManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsUserForWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableWorkloadIdentityRbac) {
  name: guid(keyVault.id, workerManagedIdentity.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalId: workerManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsUserForSchedulers 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableWorkloadIdentityRbac) {
  name: guid(keyVault.id, schedulersManagedIdentity.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalId: schedulersManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsOfficerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (keyVaultOfficerObjectId != '') {
  name: guid(keyVault.id, keyVaultOfficerObjectId, 'KeyVaultSecretsOfficer')
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsOfficerRoleDefinitionId
    principalId: keyVaultOfficerObjectId
    principalType: 'ServicePrincipal'
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointName
  location: location
  tags: modulesTags
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointName
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: [
            'vault'
          ]
        }
      }
    ]
  }
}

resource privateEndpointDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${privateEndpointName}'
  scope: privateEndpoint
  properties: {
    level: lockKind
  }
}

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = if (!enableCentralizedPrivateDns) {
  name: privateDnsZoneName
  location: 'global'
  tags: modulesTags
}

resource privateDnsZoneDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (!enableCentralizedPrivateDns && lockKind != '') {
  name: 'del-lock-${privateDnsZoneName}'
  scope: privateDnsZone
  properties: {
    level: lockKind
  }
}

resource privateDnsZoneVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (!enableCentralizedPrivateDns) {
  parent: privateDnsZone
  name: privateDnsVnetLinkName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = if (!enableCentralizedPrivateDns) {
  parent: privateEndpoint
  name: privateDnsZoneGroupName
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-vaultcore-azure-net'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output keyVaultNameOutput string = keyVault.name
output keyVaultIdOutput string = keyVault.id
