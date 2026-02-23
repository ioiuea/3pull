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

@description('Storage Account 名')
param storageAccountName string

@description('Blob コンテナ名')
param blobContainerName string

@description('Blob 用 Private Endpoint 名')
param privateEndpointBlobName string

@description('File 用 Private Endpoint 名')
param privateEndpointFileName string

@description('Queue 用 Private Endpoint 名')
param privateEndpointQueueName string

@description('Table 用 Private Endpoint 名')
param privateEndpointTableName string

@description('Blob 用 Private DNS ゾーン名')
param privateDnsZoneBlobName string = 'privatelink.blob.${environment().suffixes.storage}'

@description('File 用 Private DNS ゾーン名')
param privateDnsZoneFileName string = 'privatelink.file.${environment().suffixes.storage}'

@description('Queue 用 Private DNS ゾーン名')
param privateDnsZoneQueueName string = 'privatelink.queue.${environment().suffixes.storage}'

@description('Table 用 Private DNS ゾーン名')
param privateDnsZoneTableName string = 'privatelink.table.${environment().suffixes.storage}'

@description('Blob 用 Private DNS ゾーングループ名')
param privateDnsZoneGroupBlobName string

@description('File 用 Private DNS ゾーングループ名')
param privateDnsZoneGroupFileName string

@description('Queue 用 Private DNS ゾーングループ名')
param privateDnsZoneGroupQueueName string

@description('Table 用 Private DNS ゾーングループ名')
param privateDnsZoneGroupTableName string

@description('Blob 用 Private DNS 仮想ネットワークリンク名')
param privateDnsVnetLinkBlobName string

@description('File 用 Private DNS 仮想ネットワークリンク名')
param privateDnsVnetLinkFileName string

@description('Queue 用 Private DNS 仮想ネットワークリンク名')
param privateDnsVnetLinkQueueName string

@description('Table 用 Private DNS 仮想ネットワークリンク名')
param privateDnsVnetLinkTableName string

@description('Storage Account SKU 名')
param blobSkuName string = 'Standard_LRS'

@description('Storage Account Kind')
param blobKind string = 'StorageV2'

@description('Storage Account Access Tier')
param blobAccessTier string = 'Hot'

@description('Storage Account の public network access')
param publicNetworkAccess string = 'Disabled'

@description('BLOB の論理的な削除を有効化するか')
param enableBlobSoftDelete bool = true

@description('BLOB の論理削除保持日数')
param blobDeleteRetentionDays int = 7

@description('コンテナーの論理的な削除を有効化するか')
param enableContainerSoftDelete bool = true

@description('コンテナー論理削除保持日数')
param containerDeleteRetentionDays int = 7

@description('BLOB バージョン管理を有効化するか')
param enableBlobVersioning bool = true

@description('集約 Private DNS を利用する場合は true')
param enableCentralizedPrivateDns bool = false

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: modulesTags
  kind: blobKind
  sku: {
    name: blobSkuName
  }
  properties: {
    accessTier: blobAccessTier
    publicNetworkAccess: publicNetworkAccess
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: blobContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: enableBlobSoftDelete
      days: blobDeleteRetentionDays
    }
    containerDeleteRetentionPolicy: {
      enabled: enableContainerSoftDelete
      days: containerDeleteRetentionDays
    }
    isVersioningEnabled: enableBlobVersioning
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource storageAccountDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${storageAccountName}'
  scope: storageAccount
  properties: {
    level: lockKind
  }
}

resource storageAccountDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: blobService
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
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
      }
    ]
  }
}

resource fileServiceDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: fileService
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
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
      }
    ]
  }
}

resource queueServiceDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: queueService
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
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
      }
    ]
  }
}

resource tableServiceDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: tableService
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
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
      }
    ]
  }
}

resource privateEndpointBlob 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointBlobName
  location: location
  tags: modulesTags
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointBlobName
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

resource privateEndpointFile 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointFileName
  location: location
  tags: modulesTags
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointFileName
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'file'
          ]
        }
      }
    ]
  }
}

resource privateEndpointQueue 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointQueueName
  location: location
  tags: modulesTags
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointQueueName
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'queue'
          ]
        }
      }
    ]
  }
}

resource privateEndpointTable 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointTableName
  location: location
  tags: modulesTags
  properties: {
    subnet: {
      id: privateEndpointSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointTableName
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'table'
          ]
        }
      }
    ]
  }
}

resource privateEndpointBlobDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${privateEndpointBlobName}'
  scope: privateEndpointBlob
  properties: {
    level: lockKind
  }
}

resource privateEndpointFileDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${privateEndpointFileName}'
  scope: privateEndpointFile
  properties: {
    level: lockKind
  }
}

resource privateEndpointQueueDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${privateEndpointQueueName}'
  scope: privateEndpointQueue
  properties: {
    level: lockKind
  }
}

resource privateEndpointTableDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${privateEndpointTableName}'
  scope: privateEndpointTable
  properties: {
    level: lockKind
  }
}

resource privateDnsZoneBlob 'Microsoft.Network/privateDnsZones@2024-06-01' = if (!enableCentralizedPrivateDns) {
  name: privateDnsZoneBlobName
  location: 'global'
  tags: modulesTags
}

resource privateDnsZoneFile 'Microsoft.Network/privateDnsZones@2024-06-01' = if (!enableCentralizedPrivateDns) {
  name: privateDnsZoneFileName
  location: 'global'
  tags: modulesTags
}

resource privateDnsZoneQueue 'Microsoft.Network/privateDnsZones@2024-06-01' = if (!enableCentralizedPrivateDns) {
  name: privateDnsZoneQueueName
  location: 'global'
  tags: modulesTags
}

resource privateDnsZoneTable 'Microsoft.Network/privateDnsZones@2024-06-01' = if (!enableCentralizedPrivateDns) {
  name: privateDnsZoneTableName
  location: 'global'
  tags: modulesTags
}

resource privateDnsZoneBlobDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (!enableCentralizedPrivateDns && lockKind != '') {
  name: 'del-lock-${privateDnsZoneBlobName}'
  scope: privateDnsZoneBlob
  properties: {
    level: lockKind
  }
}

resource privateDnsZoneFileDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (!enableCentralizedPrivateDns && lockKind != '') {
  name: 'del-lock-${privateDnsZoneFileName}'
  scope: privateDnsZoneFile
  properties: {
    level: lockKind
  }
}

resource privateDnsZoneQueueDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (!enableCentralizedPrivateDns && lockKind != '') {
  name: 'del-lock-${privateDnsZoneQueueName}'
  scope: privateDnsZoneQueue
  properties: {
    level: lockKind
  }
}

resource privateDnsZoneTableDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (!enableCentralizedPrivateDns && lockKind != '') {
  name: 'del-lock-${privateDnsZoneTableName}'
  scope: privateDnsZoneTable
  properties: {
    level: lockKind
  }
}

resource privateDnsZoneBlobVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (!enableCentralizedPrivateDns) {
  parent: privateDnsZoneBlob
  name: privateDnsVnetLinkBlobName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource privateDnsZoneFileVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (!enableCentralizedPrivateDns) {
  parent: privateDnsZoneFile
  name: privateDnsVnetLinkFileName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource privateDnsZoneQueueVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (!enableCentralizedPrivateDns) {
  parent: privateDnsZoneQueue
  name: privateDnsVnetLinkQueueName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource privateDnsZoneTableVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = if (!enableCentralizedPrivateDns) {
  parent: privateDnsZoneTable
  name: privateDnsVnetLinkTableName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource privateDnsZoneGroupBlob 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = if (!enableCentralizedPrivateDns) {
  parent: privateEndpointBlob
  name: privateDnsZoneGroupBlobName
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-st-blob-core-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneBlob.id
        }
      }
    ]
  }
}

resource privateDnsZoneGroupFile 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = if (!enableCentralizedPrivateDns) {
  parent: privateEndpointFile
  name: privateDnsZoneGroupFileName
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-file-core-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneFile.id
        }
      }
    ]
  }
}

resource privateDnsZoneGroupQueue 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = if (!enableCentralizedPrivateDns) {
  parent: privateEndpointQueue
  name: privateDnsZoneGroupQueueName
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-queue-core-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneQueue.id
        }
      }
    ]
  }
}

resource privateDnsZoneGroupTable 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = if (!enableCentralizedPrivateDns) {
  parent: privateEndpointTable
  name: privateDnsZoneGroupTableName
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-table-core-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZoneTable.id
        }
      }
    ]
  }
}

output storageAccountNameOutput string = storageAccount.name
output storageAccountIdOutput string = storageAccount.id
