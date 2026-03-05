targetScope = 'resourceGroup'

@description('AKS の OIDC issuer URL')
param oidcIssuerUrl string

@description('API 用 Managed Identity 名')
param apiManagedIdentityName string

@description('worker 用 Managed Identity 名')
param workerManagedIdentityName string

@description('cleanup 用 Managed Identity 名')
param cleanupManagedIdentityName string

@description('アプリケーション Namespace')
param appNamespace string

@description('API 用 ServiceAccount 名')
param apiServiceAccountName string

@description('worker 用 ServiceAccount 名')
param workerServiceAccountName string

@description('cleanup 用 ServiceAccount 名')
param cleanupServiceAccountName string

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

@description('cleanup 用 Federated Credential 名')
param cleanupFederatedCredentialName string

@description('KEDA Operator 用 Federated Credential 名')
param kedaOperatorFederatedCredentialName string

resource apiManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: apiManagedIdentityName
}

resource workerManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: workerManagedIdentityName
}

resource cleanupManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: cleanupManagedIdentityName
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

resource cleanupFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: cleanupManagedIdentity
  name: cleanupFederatedCredentialName
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${appNamespace}:${cleanupServiceAccountName}'
    audiences: audiences
  }
}

resource kedaOperatorFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: workerManagedIdentity
  name: kedaOperatorFederatedCredentialName
  dependsOn: [
    workerFederatedCredential
  ]
  properties: {
    issuer: oidcIssuerUrl
    subject: 'system:serviceaccount:${kedaNamespace}:${kedaOperatorServiceAccountName}'
    audiences: audiences
  }
}

output apiFederatedCredentialId string = apiFederatedCredential.id
output workerFederatedCredentialId string = workerFederatedCredential.id
output cleanupFederatedCredentialId string = cleanupFederatedCredential.id
output kedaOperatorFederatedCredentialId string = kedaOperatorFederatedCredential.id
