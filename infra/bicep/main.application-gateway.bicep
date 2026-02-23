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

@description('ログアナリティクス名')
param logAnalyticsName string

@description('ログアナリティクスのリソースグループ名')
param logAnalyticsResourceGroupName string

@description('VNETの名称')
param vnetName string

@description('Application Gateway 名')
param applicationGatewayName string

@description('Application Gateway 用 Public IP 名')
param publicIPName string

@description('WAF Policy 名')
param wafPolicyName string

@description('Gateway IP Configuration 名')
param gatewayIPConfigurationName string = 'appGatewayIpConfig'

@description('Frontend Private IP Configuration 名')
param frontendPrivateIPConfigurationName string = 'appGatewayFrontendPrivateIP'

@description('Frontend Public IP Configuration 名')
param frontendPublicIPConfigurationName string = 'appGatewayFrontendPublicIP'

@description('Frontend Private IP 割り当て方式')
param frontendPrivateIPAllocationMethod string = 'Static'

@description('Frontend Private IP')
param frontendPrivateIPAddress string

@description('Frontend Port 名')
param frontendPortName string = 'appGatewayFrontendPort'

@description('Frontend Port')
param frontendPort int = 80

@description('Backend Address Pool 名')
param backendPoolName string = 'appGatewayBackendPool'

@description('Backend HTTP Settings 名')
param backendHttpSettingsName string = 'appGatewayBackendHttpSettings'

@description('Backend HTTP Port')
param backendHttpPort int = 80

@description('Backend HTTP Protocol')
param backendHttpProtocol string = 'Http'

@description('Cookie ベースのセッションアフィニティ')
param backendCookieBasedAffinity string = 'Enabled'

@description('Backend Request Timeout')
param backendRequestTimeout int = 60

@description('HTTP Listener 名')
param httpListenerName string = 'appGatewayHttpListener'

@description('Request Routing Rule 名')
param requestRoutingRuleName string = 'appGatewayRule'

@description('Probe 名')
param probeName string = 'appGatewayProbe'

@description('Probe Protocol')
param probeProtocol string = 'Http'

@description('Probe Host')
param probeHost string = 'www.contoso.com'

@description('Probe Path')
param probePath string = '/path/to/probe'

@description('Probe Interval')
param probeInterval int = 30

@description('Probe Timeout')
param probeTimeout int = 120

@description('Probe Unhealthy Threshold')
param probeUnhealthyThreshold int = 8

@description('Application Gateway SKU 名')
param appGatewaySkuName string = 'WAF_v2'

@description('Application Gateway SKU Tier')
param appGatewaySkuTier string = 'WAF_v2'

@description('Application Gateway SKU Capacity')
param appGatewaySkuCapacity int = 1

@description('Public IP SKU')
param publicIPSku string = 'Standard'

@description('Public IP 割り当て')
param publicIPAllocationMethod string = 'Static'

@description('Public IP バージョン')
param publicIPAddressVersion string = 'IPv4'

@description('DDOS保護モード')
param protectionMode string = 'Disabled'

@description('WAF mode')
param wafMode string = 'Detection'

@description('WAF state')
param wafState string = 'Enabled'

@description('WAF request body check')
param wafRequestBodyCheck bool = true

@description('WAF request body inspect limit (KB)')
param wafRequestBodyInspectLimitInKB int = 2000

@description('WAF max request body size (KB)')
param wafMaxRequestBodySizeInKb int = 2000

@description('WAF file upload limit (MB)')
param wafFileUploadLimitInMb int = 100

@description('WAF managed rule set type')
param wafRuleSetType string = 'OWASP'

@description('WAF managed rule set version')
param wafRuleSetVersion string = '3.2'

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource applicationGatewaySubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' existing = {
  name: '${vnetName}/ApplicationGatewaySubnet'
}

resource publicIP 'Microsoft.Network/publicIPAddresses@2022-07-01' = {
  name: publicIPName
  location: location
  tags: modulesTags
  sku: {
    name: publicIPSku
  }
  properties: {
    publicIPAllocationMethod: publicIPAllocationMethod
    publicIPAddressVersion: publicIPAddressVersion
    ddosSettings: {
      protectionMode: protectionMode
    }
  }
}

resource publicIPDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${publicIPName}'
  scope: publicIP
  properties: {
    level: lockKind
  }
}

resource wafPolicy 'Microsoft.Network/applicationGatewayWebApplicationFirewallPolicies@2024-07-01' = {
  name: wafPolicyName
  location: location
  tags: modulesTags
  properties: {
    customRules: []
    managedRules: {
      exclusions: []
      managedRuleSets: [
        {
          ruleSetType: wafRuleSetType
          ruleSetVersion: wafRuleSetVersion
        }
      ]
    }
    policySettings: {
      mode: wafMode
      state: wafState
      requestBodyCheck: wafRequestBodyCheck
      requestBodyInspectLimitInKB: wafRequestBodyInspectLimitInKB
      maxRequestBodySizeInKb: wafMaxRequestBodySizeInKb
      fileUploadLimitInMb: wafFileUploadLimitInMb
    }
  }
}

resource wafPolicyDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${wafPolicyName}'
  scope: wafPolicy
  properties: {
    level: lockKind
  }
}

resource applicationGateway 'Microsoft.Network/applicationGateways@2022-09-01' = {
  name: applicationGatewayName
  location: location
  tags: modulesTags
  properties: {
    sku: {
      name: appGatewaySkuName
      tier: appGatewaySkuTier
      capacity: appGatewaySkuCapacity
    }
    gatewayIPConfigurations: [
      {
        name: gatewayIPConfigurationName
        properties: {
          subnet: {
            id: applicationGatewaySubnet.id
          }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: frontendPrivateIPConfigurationName
        properties: {
          privateIPAddress: frontendPrivateIPAddress
          privateIPAllocationMethod: frontendPrivateIPAllocationMethod
          subnet: {
            id: applicationGatewaySubnet.id
          }
        }
      }
      {
        name: frontendPublicIPConfigurationName
        properties: {
          publicIPAddress: {
            id: publicIP.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: frontendPortName
        properties: {
          port: frontendPort
        }
      }
    ]
    backendAddressPools: [
      {
        name: backendPoolName
        properties: {
          backendAddresses: []
        }
      }
    ]
    probes: [
      {
        name: probeName
        properties: {
          protocol: probeProtocol
          host: probeHost
          path: probePath
          interval: probeInterval
          timeout: probeTimeout
          unhealthyThreshold: probeUnhealthyThreshold
          pickHostNameFromBackendHttpSettings: false
          minServers: 0
          match: {
            statusCodes: [
              '200-399'
            ]
          }
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: backendHttpSettingsName
        properties: {
          port: backendHttpPort
          protocol: backendHttpProtocol
          cookieBasedAffinity: backendCookieBasedAffinity
          requestTimeout: backendRequestTimeout
          probe: {
            id: '${resourceId('Microsoft.Network/applicationGateways', applicationGatewayName)}/probes/${probeName}'
          }
        }
      }
    ]
    httpListeners: [
      {
        name: httpListenerName
        properties: {
          frontendIPConfiguration: {
            id: '${resourceId('Microsoft.Network/applicationGateways', applicationGatewayName)}/frontendIPConfigurations/${frontendPrivateIPConfigurationName}'
          }
          frontendPort: {
            id: '${resourceId('Microsoft.Network/applicationGateways', applicationGatewayName)}/frontendPorts/${frontendPortName}'
          }
          protocol: 'Http'
        }
      }
    ]
    requestRoutingRules: [
      {
        name: requestRoutingRuleName
        properties: {
          ruleType: 'Basic'
          httpListener: {
            id: '${resourceId('Microsoft.Network/applicationGateways', applicationGatewayName)}/httpListeners/${httpListenerName}'
          }
          backendAddressPool: {
            id: '${resourceId('Microsoft.Network/applicationGateways', applicationGatewayName)}/backendAddressPools/${backendPoolName}'
          }
          backendHttpSettings: {
            id: '${resourceId('Microsoft.Network/applicationGateways', applicationGatewayName)}/backendHttpSettingsCollection/${backendHttpSettingsName}'
          }
          priority: 1
        }
      }
    ]
    firewallPolicy: {
      id: wafPolicy.id
    }
  }
}

resource applicationGatewayDiagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diagnostic-to-${logAnalyticsName}'
  scope: applicationGateway
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

resource applicationGatewayDeleteLock 'Microsoft.Authorization/locks@2020-05-01' = if (lockKind != '') {
  name: 'del-lock-${applicationGatewayName}'
  scope: applicationGateway
  properties: {
    level: lockKind
  }
}

output publicIPResourceId string = publicIP.id
output wafPolicyResourceId string = wafPolicy.id
output applicationGatewayResourceId string = applicationGateway.id
