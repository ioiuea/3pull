targetScope = 'resourceGroup'

@description('環境名')
param environmentName string

@description('システム名称')
param systemName string

@description('デプロイ先リージョン')
param location string

@description('モジュール名')
param modulesName string = 'nw'

@description('ロック')
param lockKind string = 'CanNotDelete'

@description('Route Table 定義')
param routeTables array

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource routeTableResources 'Microsoft.Network/routeTables@2024-07-01' = [
  for routeTable in routeTables: {
    name: 'rt-${environmentName}-${systemName}-${routeTable.name}'
    location: location
    tags: modulesTags
    properties: {
      disableBgpRoutePropagation: routeTable.?disableBgpRoutePropagation ?? false
      routes: routeTable.routes
    }
  }
]

resource routeTableLocks 'Microsoft.Authorization/locks@2020-05-01' = [
  for (routeTable, i) in routeTables: if (lockKind != '') {
    name: 'del-lock-rt-${environmentName}-${systemName}-${routeTable.name}'
    scope: routeTableResources[i]
    properties: {
      level: lockKind
    }
  }
]

output routeTableNames array = [for routeTable in routeTables: 'rt-${environmentName}-${systemName}-${routeTable.name}']
