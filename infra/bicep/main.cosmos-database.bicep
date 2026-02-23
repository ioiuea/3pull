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

@description('Cosmos DB account 名')
param cosmosAccountName string

@description('SQL Database 名')
param sqlDatabaseName string

@description('public network access')
param publicNetworkAccess string = 'Disabled'

@description('スループット方式')
param throughputMode string = 'Serverless'

@description('Manual RU/s')
param manualThroughputRu int = 400

@description('Autoscale 最大 RU/s')
param autoscaleMaxThroughputRu int = 1000

@description('バックアップ方式')
param backupPolicyType string = 'Periodic'

@description('Periodic バックアップ間隔 (分)')
param periodicBackupIntervalInMinutes int = 240

@description('Periodic バックアップ保持時間 (時間)')
param periodicBackupRetentionIntervalInHours int = 8

@description('Periodic バックアップ冗長性')
param periodicBackupStorageRedundancy string = 'Geo'

@description('Continuous バックアップティア')
param continuousBackupTier string = 'Continuous30Days'

@description('DR 用セカンダリリージョン')
param failoverRegions array = []

@description('自動フェールオーバー')
param enableAutomaticFailover bool = false

@description('複数リージョン書き込み')
param enableMultipleWriteLocations bool = false

@description('既定整合性レベル')
param consistencyLevel string = 'Session'

@description('ローカル認証無効化')
param disableLocalAuth bool = false

@description('キーベースメタデータ書き込み無効化')
param disableKeyBasedMetadataWriteAccess bool = false

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string = 'privatelink.documents.azure.com'

@description('Private DNS ゾーングループ名')
param privateDnsZoneGroupName string

@description('Private DNS 仮想ネットワークリンク名')
param privateDnsVnetLinkName string

@description('集約 Private DNS を利用する場合は true')
param enableCentralizedPrivateDns bool = false

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

var secondaryLocations = [
  for (region, i) in failoverRegions: {
    locationName: string(region)
    failoverPriority: i + 1
    isZoneRedundant: false
  }
]

var accountLocations = concat(
  [
    {
      locationName: location
      failoverPriority: 0
      isZoneRedundant: false
    }
  ],
  secondaryLocations
)

var consistencyPolicy = consistencyLevel == 'BoundedStaleness'
  ? {
      defaultConsistencyLevel: 'BoundedStaleness'
      maxIntervalInSeconds: 5
      maxStalenessPrefix: 100
    }
  : {
      defaultConsistencyLevel: consistencyLevel
    }

var backupPolicy = backupPolicyType == 'Periodic'
  ? {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: periodicBackupIntervalInMinutes
        backupRetentionIntervalInHours: periodicBackupRetentionIntervalInHours
        backupStorageRedundancy: periodicBackupStorageRedundancy
      }
    }
  : {
      type: 'Continuous'
      continuousModeProperties: {
        tier: continuousBackupTier
      }
    }

var sqlDatabaseProperties = union(
  {
    resource: {
      id: sqlDatabaseName
    }
  },
  throughputMode == 'Manual'
    ? {
        options: {
          throughput: manualThroughputRu
        }
      }
    : throughputMode == 'Autoscale'
        ? {
            options: {
              autoscaleSettings: {
                maxThroughput: autoscaleMaxThroughputRu
              }
            }
          }
        : {}
)

var cosmosCapacityMode = throughputMode == 'Serverless' ? 'Serverless' : 'Provisioned'

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: cosmosAccountName
  location: location
  tags: modulesTags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    publicNetworkAccess: publicNetworkAccess
    locations: accountLocations
    capacityMode: cosmosCapacityMode
    consistencyPolicy: consistencyPolicy
    enableAutomaticFailover: enableAutomaticFailover
    enableMultipleWriteLocations: enableMultipleWriteLocations
    disableLocalAuth: disableLocalAuth
    disableKeyBasedMetadataWriteAccess: disableKeyBasedMetadataWriteAccess
    backupPolicy: backupPolicy
  }
}

resource sqlDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmosAccount
  name: sqlDatabaseName
  properties: {
    ...sqlDatabaseProperties
  }
}

resource cosmosAccountDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${cosmosAccountName}'
  scope: cosmosAccount
  properties: {
    level: lockKind
  }
}

resource cosmosAccountDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: cosmosAccount
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
      }
    ]
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
          privateLinkServiceId: cosmosAccount.id
          groupIds: [
            'Sql'
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
        name: 'privatelink-documents-azure-com'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output cosmosAccountId string = cosmosAccount.id
output cosmosAccountName string = cosmosAccount.name
output sqlDatabaseId string = sqlDatabase.id
