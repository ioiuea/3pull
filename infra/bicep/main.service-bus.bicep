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

@description('keda-operator 用 Managed Identity 名')
param kedaOperatorManagedIdentityName string

@description('Workload Identity 用 RBAC 付与を有効化')
param enableWorkloadIdentityRbac bool = true

@description('Service Bus Namespace 名')
param serviceBusNamespaceName string

@description('Service Bus SKU')
param serviceBusSkuName string = 'Standard'

@description('Service Bus SKU capacity')
param serviceBusSkuCapacity int = 1

@description('Service Bus の public network access')
param publicNetworkAccess string = 'Disabled'

@description('Service Bus 最小 TLS バージョン')
param minimumTlsVersion string = '1.2'

@description('Service Bus ローカル認証（SAS）を無効化するか')
param disableLocalAuth bool = true

@description('Service Bus ゾーン冗長化')
param zoneRedundant bool = false

@description('作成する Service Bus Queue 名一覧')
param queueNames array = []

@description('API 用 MI に付与する Service Bus Data Sender の roleDefinitionId')
param serviceBusDataSenderRoleDefinitionId string

@description('worker 用 MI に付与する Service Bus Data Receiver の roleDefinitionId')
param serviceBusDataReceiverRoleDefinitionId string

@description('Private Endpoint 名')
param privateEndpointName string

@description('Private DNS ゾーン名')
param privateDnsZoneName string = 'privatelink.servicebus.windows.net'

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

resource kedaOperatorManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  scope: resourceGroup(managedIdentityResourceGroupName)
  name: kedaOperatorManagedIdentityName
}

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2023-01-01-preview' = {
  name: serviceBusNamespaceName
  location: location
  tags: modulesTags
  sku: {
    name: serviceBusSkuName
    tier: serviceBusSkuName
    capacity: serviceBusSkuCapacity
  }
  properties: {
    publicNetworkAccess: publicNetworkAccess
    minimumTlsVersion: minimumTlsVersion
    disableLocalAuth: disableLocalAuth
    zoneRedundant: zoneRedundant
  }
}

resource serviceBusQueues 'Microsoft.ServiceBus/namespaces/queues@2023-01-01-preview' = [
  for queueName in queueNames: {
    parent: serviceBusNamespace
    name: string(queueName)
    properties: {}
  }
]

resource serviceBusDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${serviceBusNamespaceName}'
  scope: serviceBusNamespace
  properties: {
    level: lockKind
  }
}

resource serviceBusDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: serviceBusNamespace
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

resource serviceBusSenderForApi 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableWorkloadIdentityRbac) {
  name: guid(serviceBusNamespace.id, apiManagedIdentity.id, serviceBusDataSenderRoleDefinitionId)
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: serviceBusDataSenderRoleDefinitionId
    principalId: apiManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource serviceBusReceiverForWorker 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableWorkloadIdentityRbac) {
  name: guid(serviceBusNamespace.id, workerManagedIdentity.id, serviceBusDataReceiverRoleDefinitionId)
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: serviceBusDataReceiverRoleDefinitionId
    principalId: workerManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource serviceBusReceiverForKedaOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableWorkloadIdentityRbac) {
  name: guid(serviceBusNamespace.id, kedaOperatorManagedIdentity.id, serviceBusDataReceiverRoleDefinitionId)
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: serviceBusDataReceiverRoleDefinitionId
    principalId: kedaOperatorManagedIdentity.properties.principalId
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
          privateLinkServiceId: serviceBusNamespace.id
          groupIds: [
            'namespace'
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
        name: 'privatelink-servicebus-windows-net'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output serviceBusNamespaceNameOutput string = serviceBusNamespace.name
output serviceBusNamespaceIdOutput string = serviceBusNamespace.id
