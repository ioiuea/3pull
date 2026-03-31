targetScope = 'resourceGroup'

@description('環境名')
param environmentName string

@description('システム名称')
param systemName string

@description('デプロイ先リージョン')
param location string

@description('モジュール名')
param modulesName string = 'svc'

@description('低遅延系 Application Gateway サブネット有効化')
param enableLowLatencyApplicationGatewaySubnet bool = false

var modulesTags = {
  environmentName: environmentName
  systemName: systemName
  modulesName: modulesName
  createdBy: 'bicep'
  billing: 'infra'
}

resource apiManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-api'
  location: location
  tags: modulesTags
}

resource workerManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-worker'
  location: location
  tags: modulesTags
}

resource schedulersManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-schedulers'
  location: location
  tags: modulesTags
}

resource migrationManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-migration'
  location: location
  tags: modulesTags
}

resource redisOpsManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-redis-ops'
  location: location
  tags: modulesTags
}

resource aksOperatorManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-aks-operator'
  location: location
  tags: modulesTags
}

resource aksAdminManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-aks-admin'
  location: location
  tags: modulesTags
}

resource acrAdminManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-acr-admin'
  location: location
  tags: modulesTags
}

resource kvAdminManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-kv-admin'
  location: location
  tags: modulesTags
}

resource kedaOperatorManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-keda-operator'
  location: location
  tags: modulesTags
}

resource agicStandardManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${environmentName}-${systemName}-agic-standard'
  location: location
  tags: modulesTags
}

resource agicLowLatencyManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (enableLowLatencyApplicationGatewaySubnet) {
  name: 'mi-${environmentName}-${systemName}-agic-lowlatency'
  location: location
  tags: modulesTags
}

output apiManagedIdentityName string = apiManagedIdentity.name
output apiManagedIdentityPrincipalId string = apiManagedIdentity.properties.principalId
output workerManagedIdentityName string = workerManagedIdentity.name
output workerManagedIdentityPrincipalId string = workerManagedIdentity.properties.principalId
output schedulersManagedIdentityName string = schedulersManagedIdentity.name
output schedulersManagedIdentityPrincipalId string = schedulersManagedIdentity.properties.principalId
output migrationManagedIdentityName string = migrationManagedIdentity.name
output migrationManagedIdentityPrincipalId string = migrationManagedIdentity.properties.principalId
output redisOpsManagedIdentityName string = redisOpsManagedIdentity.name
output aksOperatorManagedIdentityName string = aksOperatorManagedIdentity.name
output aksAdminManagedIdentityName string = aksAdminManagedIdentity.name
output acrAdminManagedIdentityName string = acrAdminManagedIdentity.name
output acrAdminManagedIdentityPrincipalId string = acrAdminManagedIdentity.properties.principalId
output kvAdminManagedIdentityName string = kvAdminManagedIdentity.name
output kvAdminManagedIdentityPrincipalId string = kvAdminManagedIdentity.properties.principalId
output kedaOperatorManagedIdentityName string = kedaOperatorManagedIdentity.name
output agicStandardManagedIdentityName string = agicStandardManagedIdentity.name
output agicLowLatencyManagedIdentityName string = enableLowLatencyApplicationGatewaySubnet ? agicLowLatencyManagedIdentity!.name : ''
