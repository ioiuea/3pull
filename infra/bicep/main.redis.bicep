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

@description('Redis 名')
param redisName string

@description('public network access')
param publicNetworkAccess string = 'Disabled'

@description('最小 TLS バージョン')
param minimumTlsVersion string = '1.2'

@description('非SSLポートを有効化するか')
param enableNonSslPort bool = false

@description('SKU 名')
param skuName string = 'Basic'

@description('SKU ファミリー')
param skuFamily string = 'C'

@description('SKU 容量')
param skuCapacity int = 0

@description('シャード数')
param shardCount int = 1

@description('ゾーン割り当てポリシー')
param zonalAllocationPolicy string = 'Automatic'

@description('ゾーン配列')
param zones array = []

@description('Primary あたりのレプリカ数')
param replicasPerMaster int = 1

@description('Geo レプリケーションを有効化するか（現時点では将来拡張用）')
param enableGeoReplication bool = false

@description('Microsoft Entra 認証を有効化するか')
param enableMicrosoftEntraAuthentication bool = true

@description('AccessKey 認証を無効化するか')
param disableAccessKeyAuthentication bool = false

@description('カスタムメンテナンスウィンドウ')
param enableCustomMaintenanceWindow bool = false

@description('メンテナンス曜日 (0-6)')
param maintenanceWindowDayOfWeek int = 0

@description('メンテナンス開始時 (UTC hour)')
param maintenanceWindowStartHour int = 3

@description('メンテナンス時間 (ISO 8601)')
param maintenanceWindowDuration string = 'PT5H'

@description('RDB バックアップを有効化するか')
param enableRdbBackup bool = false

@description('RDB バックアップ間隔(分)')
param rdbBackupFrequencyInMinutes int = 60

@description('RDB スナップショット保持数')
param rdbBackupMaxSnapshotCount int = 1

@description('RDB 保存先接続文字列')
@secure()
param rdbStorageConnectionString string = ''

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string = 'privatelink.redis.cache.windows.net'

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

var maintenanceDayLabels = [
  'Sunday'
  'Monday'
  'Tuesday'
  'Wednesday'
  'Thursday'
  'Friday'
  'Saturday'
]

var selectedMaintenanceDay = maintenanceDayLabels[maintenanceWindowDayOfWeek]
var isPremium = skuName == 'Premium'
var useUserDefinedZones = isPremium && zonalAllocationPolicy == 'UserDefined' && length(zones) > 0

var redisPropertiesBase = {
  sku: {
    name: skuName
    family: skuFamily
    capacity: skuCapacity
  }
  enableNonSslPort: enableNonSslPort
  minimumTlsVersion: minimumTlsVersion
  publicNetworkAccess: publicNetworkAccess
  disableAccessKeyAuthentication: disableAccessKeyAuthentication
  redisConfiguration: {
    'aad-enabled': enableMicrosoftEntraAuthentication ? 'true' : 'false'
  }
}

var redisPropertiesPremium = isPremium
  ? {
      shardCount: shardCount
      replicasPerMaster: replicasPerMaster
      zonalAllocationPolicy: zonalAllocationPolicy
    }
  : {}

var redisPropertiesPremiumRdb = isPremium && enableRdbBackup
  ? {
      redisConfiguration: {
        'rdb-backup-enabled': 'true'
        'rdb-backup-frequency': string(rdbBackupFrequencyInMinutes)
        'rdb-backup-max-snapshot-count': string(rdbBackupMaxSnapshotCount)
        'rdb-storage-connection-string': rdbStorageConnectionString
      }
    }
  : {}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
}

resource redisCache 'Microsoft.Cache/Redis@2024-11-01' = {
  name: redisName
  location: location
  tags: modulesTags
  zones: useUserDefinedZones ? zones : null
  properties: union(redisPropertiesBase, redisPropertiesPremium, redisPropertiesPremiumRdb)
}

resource redisPatchSchedule 'Microsoft.Cache/Redis/patchSchedules@2024-11-01' = if (enableCustomMaintenanceWindow) {
  parent: redisCache
  name: 'default'
  properties: {
    scheduleEntries: [
      {
        dayOfWeek: selectedMaintenanceDay
        startHourUtc: maintenanceWindowStartHour
        maintenanceWindow: maintenanceWindowDuration
      }
    ]
  }
}

resource redisCacheDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${redisName}'
  scope: redisCache
  properties: {
    level: lockKind
  }
}

resource redisCacheDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: redisCache
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
          privateLinkServiceId: redisCache.id
          groupIds: [
            'redisCache'
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
        name: 'privatelink-redis-cache-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output redisCacheId string = redisCache.id
output redisCacheName string = redisCache.name
output enableGeoReplicationRequested bool = enableGeoReplication
