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

@description('API 用 Managed Identity の principalId')
param apiManagedIdentityPrincipalId string = ''

@description('Access Policy Assignment を有効化')
param enableAccessPolicyAssignment bool = true

@description('Redis ops 用 Managed Identity の principalId')
param redisOpsManagedIdentityPrincipalId string = ''

@description('Redis ops 用 Access Policy Assignment を有効化')
param enableRedisOpsAccessPolicyAssignment bool = true

@description('Redis 名')
param redisName string

@description('最小 TLS バージョン')
param minimumTlsVersion string = '1.2'

@description('Public Network Access')
param publicNetworkAccess string = 'Disabled'

@description('Redis SKU 名')
param redisSkuName string = 'Balanced_B0'

@description('高可用性設定')
param highAvailability string = 'Enabled'

@description('Database 名')
param databaseName string = 'default'

@description('割り当てる Access Policy 名')
param accessPolicyName string = 'default'

@description('Access Key 認証設定')
param accessKeysAuthentication string = 'Disabled'

@description('クライアント接続プロトコル')
param clientProtocol string = 'Encrypted'

@description('クラスタリングポリシー')
param clusteringPolicy string = 'OSSCluster'

@description('Redis 接続ポート')
param redisPort int = 10000

@description('ゾーン配列')
param zones array = []

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string = 'privatelink.redis.azure.net'

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

var redisSku = startsWith(redisSkuName, 'EnterpriseFlash_')
  ? {
      name: redisSkuName
      capacity: 3
    }
  : startsWith(redisSkuName, 'Enterprise_')
  ? {
      name: redisSkuName
      capacity: 2
    }
  : {
      name: redisSkuName
    }

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  scope: resourceGroup(vnetResourceGroupName)
  name: vnetName
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  parent: virtualNetwork
  name: 'PrivateEndpointSubnet'
}

resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2025-08-01-preview' = {
  name: redisName
  location: location
  tags: modulesTags
  zones: length(zones) > 0 ? zones : null
  properties: {
    highAvailability: highAvailability
    minimumTlsVersion: minimumTlsVersion
    publicNetworkAccess: publicNetworkAccess
    encryption: {}
  }
  sku: redisSku
}

resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2025-08-01-preview' = {
  parent: redisEnterprise
  name: databaseName
  properties: {
    accessKeysAuthentication: accessKeysAuthentication
    clientProtocol: clientProtocol
    clusteringPolicy: clusteringPolicy
    port: redisPort
  }
}

resource redisAccessPolicyAssignment 'Microsoft.Cache/redisEnterprise/databases/accessPolicyAssignments@2025-07-01' = if (enableAccessPolicyAssignment) {
  parent: redisDatabase
  name: 'apiDataOwner'
  properties: {
    accessPolicyName: accessPolicyName
    user: {
      objectId: apiManagedIdentityPrincipalId
    }
  }
}

resource redisOpsAccessPolicyAssignment 'Microsoft.Cache/redisEnterprise/databases/accessPolicyAssignments@2025-07-01' = if (enableRedisOpsAccessPolicyAssignment) {
  parent: redisDatabase
  name: 'redisOpsDataOwner'
  properties: {
    accessPolicyName: accessPolicyName
    user: {
      objectId: redisOpsManagedIdentityPrincipalId
    }
  }
}

resource redisDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${redisName}'
  scope: redisEnterprise
  properties: {
    level: lockKind
  }
}

resource redisDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: redisEnterprise
  properties: {
    workspaceId: resourceId(logAnalyticsResourceGroupName, 'Microsoft.OperationalInsights/workspaces', logAnalyticsName)
    logAnalyticsDestinationType: 'Dedicated'
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
          privateLinkServiceId: redisEnterprise.id
          groupIds: [
            'redisEnterprise'
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
        name: 'privatelink-redis-azure-net'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output redisId string = redisEnterprise.id
output redisNameOutput string = redisEnterprise.name
output redisHost string = '${redisName}.${location}.redis.azure.net'
output redisPortOutput int = redisPort
