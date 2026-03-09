targetScope = 'resourceGroup'

@description('AKS の OIDC issuer URL')
param oidcIssuerUrl string

@description('API 用 Managed Identity 名')
param apiManagedIdentityName string

@description('worker 用 Managed Identity 名')
param workerManagedIdentityName string

@description('schedulers 用 Managed Identity 名')
param schedulersManagedIdentityName string

@description('KEDA Operator 用 Managed Identity 名')
param kedaOperatorManagedIdentityName string

@description('AGIC 通常系用 Managed Identity 名')
param agicStandardManagedIdentityName string

@description('AGIC 低遅延系用 Managed Identity 名')
param agicLowLatencyManagedIdentityName string = ''

@description('アプリケーション Namespace')
param appNamespace string

@description('API 用 ServiceAccount 名')
param apiServiceAccountName string

@description('worker 用 ServiceAccount 名')
param workerServiceAccountName string

@description('schedulers 用 ServiceAccount 名')
param schedulersServiceAccountName string

@description('AGIC Namespace')
param agicNamespace string = 'ingress'

@description('AGIC 通常系 ServiceAccount 名')
param agicStandardServiceAccountName string = 'sa-agic-standard'

@description('AGIC 低遅延系 ServiceAccount 名')
param agicLowLatencyServiceAccountName string = 'sa-agic-lowlatency'

@description('KEDA Namespace')
param kedaNamespace string = 'keda'

@description('KEDA Operator ServiceAccount 名')
param kedaOperatorServiceAccountName string = 'keda-operator'

@description('Federated Credential audience')
param audiences array = [
  'api://AzureADTokenExchange'
]

@description('API 用 Federated Credential 名')
param apiFederatedCredentialName string

@description('worker 用 Federated Credential 名')
param workerFederatedCredentialName string

@description('schedulers 用 Federated Credential 名')
param schedulersFederatedCredentialName string

@description('KEDA Operator 用 Federated Credential 名')
param kedaOperatorFederatedCredentialName string

@description('AGIC 通常系用 Federated Credential 名')
param agicStandardFederatedCredentialName string

@description('AGIC 低遅延系用 Federated Credential 名')
param agicLowLatencyFederatedCredentialName string

@description('低遅延系 Application Gateway サブネット有効化')
param enableLowLatencyApplicationGatewaySubnet bool = false

resource apiManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: apiManagedIdentityName
}

resource workerManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: workerManagedIdentityName
}

resource schedulersManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: schedulersManagedIdentityName
}

resource kedaOperatorManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: kedaOperatorManagedIdentityName
}

resource agicStandardManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: agicStandardManagedIdentityName
}

resource agicLowLatencyManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = if (enableLowLatencyApplicationGatewaySubnet) {
  name: agicLowLatencyManagedIdentityName
}

resource apiFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: apiManagedIdentity
  name: apiFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${appNamespace}:${apiServiceAccountName}'
    audiences: audiences
  }
}

resource workerFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: workerManagedIdentity
  name: workerFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${appNamespace}:${workerServiceAccountName}'
    audiences: audiences
  }
}

resource schedulersFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: schedulersManagedIdentity
  name: schedulersFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${appNamespace}:${schedulersServiceAccountName}'
    audiences: audiences
  }
}

resource kedaOperatorFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: kedaOperatorManagedIdentity
  name: kedaOperatorFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${kedaNamespace}:${kedaOperatorServiceAccountName}'
    audiences: audiences
  }
}

resource agicStandardFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: agicStandardManagedIdentity
  name: agicStandardFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${agicNamespace}:${agicStandardServiceAccountName}'
    audiences: audiences
  }
}

resource agicLowLatencyFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = if (enableLowLatencyApplicationGatewaySubnet) {
  parent: agicLowLatencyManagedIdentity
  name: agicLowLatencyFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${agicNamespace}:${agicLowLatencyServiceAccountName}'
    audiences: audiences
  }
}

output apiFederatedCredentialId string = apiFederatedCredential.id
output workerFederatedCredentialId string = workerFederatedCredential.id
output schedulersFederatedCredentialId string = schedulersFederatedCredential.id
output kedaOperatorFederatedCredentialId string = kedaOperatorFederatedCredential.id
output agicStandardFederatedCredentialId string = agicStandardFederatedCredential.id
output agicLowLatencyFederatedCredentialId string = enableLowLatencyApplicationGatewaySubnet ? agicLowLatencyFederatedCredential!.id : ''
