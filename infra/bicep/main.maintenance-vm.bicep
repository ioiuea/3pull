targetScope = 'resourceGroup'

@description('環境名')
param environmentName string

@description('システム名称')
param systemName string

@description('デプロイ先リージョン')
param location string

@description('モジュール名')
param modulesName string = 'maint'

@description('VNETのリソースグループ')
param nwResourceGroup string

@description('VNETの名称')
param vnetName string

@description('ロック')
param lockKind string = 'CanNotDelete'

@description('ログアナリティクス名')
param logAnalyticsName string

@description('ログアナリティクスのリソースグループ名')
param logAnalyticsResourceGroupName string

@description('maint 用 NIC 名')
param maintNicName string

@description('maint 用サブネット名')
param maintSubnetName string

@description('maint 用仮想マシン名')
param maintVmName string

@description('maint 用仮想マシンサイズ')
param maintVmSize string = 'Standard_D4as_v5'

@description('管理者ユーザー名')
param maintVmAdminUsername string = 'adminUser'

@description('管理者パスワード')
@secure()
param maintVmAdminPassword string

@description('OS イメージ情報')
param maintVmImageReference object

@description('OS ディスク情報')
param maintVmOsDisk object

@description('ブート診断の有効化')
param maintBootDiagnosticsEnabled bool = true

@description('セキュリティタイプ')
param maintSecurityType string = 'TrustedLaunch'

@description('セキュアブートの有効化')
param maintSecureBootEnabled bool = true

@description('vTPMの有効化')
param maintVTpmEnabled bool = true

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

var maintOsDisk = union(maintVmOsDisk, {
  name: 'disk-${maintVmName}'
})

resource nic 'Microsoft.Network/networkInterfaces@2024-07-01' = {
  name: maintNicName
  location: location
  tags: modulesTags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig'
        properties: {
          subnet: {
            id: resourceId(nwResourceGroup, 'Microsoft.Network/virtualNetworks/subnets', vnetName, maintSubnetName)
          }
          privateIPAllocationMethod: 'Dynamic'
        }
      }
    ]
  }
}

resource vm 'Microsoft.Compute/virtualMachines@2024-11-01' = {
  name: maintVmName
  location: location
  tags: modulesTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hardwareProfile: {
      vmSize: maintVmSize
    }
    osProfile: {
      computerName: maintVmName
      adminUsername: maintVmAdminUsername
      adminPassword: maintVmAdminPassword
      linuxConfiguration: {
        disablePasswordAuthentication: false
      }
    }
    storageProfile: {
      imageReference: maintVmImageReference
      osDisk: maintOsDisk
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
        }
      ]
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: maintBootDiagnosticsEnabled
      }
    }
    securityProfile: {
      securityType: maintSecurityType
      uefiSettings: {
        secureBootEnabled: maintSecureBootEnabled
        vTpmEnabled: maintVTpmEnabled
      }
    }
  }
}

resource nicDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${maintNicName}'
  scope: nic
  properties: {
    level: lockKind
  }
}

resource nicDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: nic
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

resource osDisk 'Microsoft.Compute/disks@2024-03-02' existing = {
  name: string(maintOsDisk.name)
}

resource osDiskDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${string(maintOsDisk.name)}'
  scope: osDisk
  dependsOn: [
    vm
  ]
  properties: {
    level: lockKind
  }
}

resource deleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${maintVmName}'
  scope: vm
  properties: {
    level: lockKind
  }
}

output maintVmId string = vm.id
output maintVmName string = vm.name
output maintNicId string = nic.id
output maintSubnetName string = maintSubnetName
