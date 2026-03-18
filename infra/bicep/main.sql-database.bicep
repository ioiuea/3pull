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

@description('SQL Server 名')
param sqlServerName string

@description('SQL Database 名')
param sqlDatabaseName string

@description('public network access')
param publicNetworkAccess string = 'Disabled'

@description('最小 TLS バージョン')
param minimalTlsVersion string = '1.2'

@description('SKU tier')
param skuTier string = 'Basic'

@description('SKU name')
param skuName string = 'Basic'

@description('最大サイズ (GiB)')
param maxSizeGb int = 2

@description('照合順序')
param collation string = 'SQL_Latin1_General_CP1_CI_AS'

@description('ゾーン冗長')
param zoneRedundant bool = false

@description('Microsoft Entra admin のログイン名')
param entraAdminLogin string

@description('Microsoft Entra admin の objectId')
param entraAdminObjectId string

@description('SQL Server bootstrap 管理者ログイン名')
param sqlAdminLogin string = ''

@secure()
@description('SQL Server bootstrap 管理者パスワード')
param sqlAdminPassword string = ''

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string

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

var maxSizeBytes = int(maxSizeGb) * 1024 * 1024 * 1024

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
}

resource sqlServer 'Microsoft.Sql/servers@2021-11-01' = {
  name: sqlServerName
  location: location
  tags: modulesTags
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    publicNetworkAccess: publicNetworkAccess
    minimalTlsVersion: minimalTlsVersion
  }
}

resource sqlServerEntraAdministrator 'Microsoft.Sql/servers/administrators@2021-11-01' = {
  parent: sqlServer
  name: 'ActiveDirectory'
  properties: {
    administratorType: 'ActiveDirectory'
    login: entraAdminLogin
    sid: entraAdminObjectId
    tenantId: tenant().tenantId
  }
}

resource sqlServerDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${sqlServerName}'
  scope: sqlServer
  properties: {
    level: lockKind
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2021-11-01' = {
  parent: sqlServer
  name: sqlDatabaseName
  location: location
  tags: modulesTags
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    collation: collation
    maxSizeBytes: maxSizeBytes
    zoneRedundant: zoneRedundant
  }
}

resource sqlDatabaseDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${sqlDatabaseName}'
  scope: sqlDatabase
  properties: {
    level: lockKind
  }
}

resource sqlDatabaseDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: sqlDatabase
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
        category: 'Basic'
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
          privateLinkServiceId: sqlServer.id
          groupIds: [
            'sqlServer'
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
        name: 'privatelink-database-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output sqlServerId string = sqlServer.id
output sqlServerNameOutput string = sqlServer.name
output sqlDatabaseId string = sqlDatabase.id
output sqlDatabaseNameOutput string = sqlDatabase.name
output privateEndpointId string = privateEndpoint.id
