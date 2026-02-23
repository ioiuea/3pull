targetScope = 'resourceGroup'

@description('VNETの名称')
param vnetName string

@description('サブネット情報')
param subnets array

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' existing = {
  name: vnetName
}

@batchSize(1)
resource subnetCreate 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = [
  for subnet in subnets: {
    parent: virtualNetwork
    name: subnet.name
    properties: {
      addressPrefix: subnet.addressPrefix
      networkSecurityGroup: null
      routeTable: null
      defaultOutboundAccess: false
      privateEndpointNetworkPolicies: subnet.?privateEndpointNetworkPolicies
    }
  }
]

output createdSubnetCount int = length(subnets)
