targetScope = 'resourceGroup'

@description('VNETの名称')
param vnetName string

@description('サブネット更新情報（NSG/RouteTable 紐づけ）')
param subnets array

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  name: vnetName
}

@batchSize(1)
resource subnetUpdate 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = [
  for subnet in subnets: {
    parent: virtualNetwork
    name: subnet.name
    properties: {
      addressPrefix: subnet.addressPrefix
      defaultOutboundAccess: false
      networkSecurityGroup: empty(subnet.networkSecurityGroupName)
        ? null
        : {
            id: resourceId('Microsoft.Network/networkSecurityGroups', subnet.networkSecurityGroupName)
          }
      routeTable: empty(subnet.routeTableName)
        ? null
        : {
            id: resourceId('Microsoft.Network/routeTables', subnet.routeTableName)
          }
      privateEndpointNetworkPolicies: subnet.?privateEndpointNetworkPolicies
    }
  }
]

output updatedSubnetCount int = length(subnets)
