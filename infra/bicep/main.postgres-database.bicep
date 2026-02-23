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

@description('PostgreSQL サーバー名')
param postgresServerName string

@description('PostgreSQL バージョン')
param postgresVersion string = '16'

@description('管理者ログイン名')
param administratorLogin string = 'pgadmin'

@description('管理者パスワード')
@secure()
param administratorPassword string

@description('public network access')
param publicNetworkAccess string = 'Disabled'

@description('SKU tier')
param skuTier string = 'Burstable'

@description('SKU name')
param skuName string = 'Standard_B2s'

@description('ストレージサイズ (GiB)')
param storageSizeGB int = 32

@description('ストレージ自動拡張')
param enableStorageAutoGrow bool = false

@description('バックアップ保持日数')
param backupRetentionDays int = 7

@description('Geo 冗長バックアップ')
param enableGeoRedundantBackup bool = false

@description('ゾーン冗長 HA')
param enableZoneRedundantHa bool = false

@description('スタンバイ AZ (未指定時は空文字)')
param standbyAvailabilityZone string = ''

@description('カスタムメンテナンスウィンドウ')
param enableCustomMaintenanceWindow bool = false

@description('メンテナンス曜日 (0-6)')
param maintenanceWindowDayOfWeek int = 0

@description('メンテナンス開始時 (UTC hour)')
param maintenanceWindowStartHour int = 3

@description('メンテナンス開始分 (UTC minute)')
param maintenanceWindowStartMinute int = 0

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string = 'privatelink.postgres.database.azure.com'

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

var autoGrowMode = enableStorageAutoGrow ? 'Enabled' : 'Disabled'
var geoRedundantBackupMode = enableGeoRedundantBackup ? 'Enabled' : 'Disabled'
var maintenanceWindowConfig = enableCustomMaintenanceWindow
  ? {
      customWindow: 'Enabled'
      dayOfWeek: maintenanceWindowDayOfWeek
      startHour: maintenanceWindowStartHour
      startMinute: maintenanceWindowStartMinute
    }
  : {
      customWindow: 'Disabled'
    }

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: location
  tags: modulesTags
  sku: {
    tier: skuTier
    name: skuName
  }
  properties: {
    version: postgresVersion
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: autoGrowMode
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: geoRedundantBackupMode
    }
    highAvailability: enableZoneRedundantHa
      ? {
          mode: 'ZoneRedundant'
          standbyAvailabilityZone: empty(standbyAvailabilityZone) ? null : standbyAvailabilityZone
        }
      : {
          mode: 'Disabled'
        }
    maintenanceWindow: maintenanceWindowConfig
    network: {
      publicNetworkAccess: publicNetworkAccess
    }
  }
}

resource postgresServerDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${postgresServerName}'
  scope: postgresServer
  properties: {
    level: lockKind
  }
}

resource postgresServerDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: postgresServer
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
          privateLinkServiceId: postgresServer.id
          groupIds: [
            'postgresqlServer'
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
        name: 'privatelink-postgres-database-azure-com'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output postgresServerId string = postgresServer.id
output postgresServerName string = postgresServer.name
output privateEndpointId string = privateEndpoint.id
